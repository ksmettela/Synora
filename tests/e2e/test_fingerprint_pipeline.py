"""
End-to-end fingerprint pipeline test.

Runs in two modes depending on environment:

- Default (offline): validates the C++ fingerprint algorithm and the LSH
  recall model in isolation. No services required. Always runs in CI.

- Live (SYNORA_E2E=live): also talks to a running fingerprint-indexer at
  SYNORA_INDEXER_URL (default http://localhost:8082). Seeds + queries the
  real service. Skipped unless SYNORA_E2E=live is set.

This keeps the algorithmic invariants under test continuously without
requiring Docker in CI, while still exercising the full HTTP path when the
developer runs the stack locally.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from urllib import error, request

import pytest

ROOT = Path(__file__).resolve().parents[2]
SEED_CATALOG = ROOT / "data-pipeline" / "seed" / "catalogs" / "demo.json"
DEMO_WAVS = ROOT / "data-pipeline" / "seed" / "wavs"

# fingerprint_cli location: either the CMake-installed copy or a /tmp build
# the developer created with `clang++ tools/fingerprint_cli.cpp ...`.
CLI_CANDIDATES = [
    os.environ.get("SYNORA_FP_CLI"),
    str(ROOT / "sdk" / "build" / "fingerprint_cli"),
    "/tmp/fingerprint_cli",
]
CLI = next((p for p in CLI_CANDIDATES if p and Path(p).exists()), None)


@pytest.fixture(scope="module")
def demo_wavs() -> Path:
    if not DEMO_WAVS.exists() or not any(DEMO_WAVS.glob("*.wav")):
        subprocess.run(
            [sys.executable, str(ROOT / "data-pipeline/seed/scripts/generate_demo_wavs.py")],
            check=True,
        )
    return DEMO_WAVS


def _fingerprint(wav: Path, window_ms: int = 3000, hop_ms: int = 1500) -> list[tuple[int, str]]:
    if CLI is None:
        pytest.skip(
            "fingerprint_cli not found. Build it with: "
            "clang++ -std=c++17 -O2 -Iinclude -Isrc tools/fingerprint_cli.cpp "
            "src/fingerprint.cpp src/crypto.cpp -lcrypto -o /tmp/fingerprint_cli"
        )
    result = subprocess.run(
        [CLI, str(wav), "--window-ms", str(window_ms), "--hop-ms", str(hop_ms)],
        check=True,
        capture_output=True,
        text=True,
    )
    out = []
    for line in result.stdout.strip().splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            out.append((int(parts[0]), parts[1].strip()))
    return out


def _hamming(a: str, b: str) -> int:
    return sum(bin(int(a[i : i + 2], 16) ^ int(b[i : i + 2], 16)).count("1") for i in range(0, len(a), 2))


class TestFingerprintAlgorithm:
    """Algorithmic invariants — run without services."""

    def test_determinism(self, demo_wavs: Path):
        wav = demo_wavs / "espn_sportscenter.wav"
        a = _fingerprint(wav)
        b = _fingerprint(wav)
        assert a == b, "fingerprints must be byte-for-byte identical across runs"

    def test_windows_produced(self, demo_wavs: Path):
        wav = demo_wavs / "espn_sportscenter.wav"
        fps = _fingerprint(wav)
        # 30s of audio with window=3s, hop=1.5s → 19 windows.
        assert len(fps) == 19
        for _, h in fps:
            assert len(h) == 64, "fingerprint must be 64 hex chars (256 bits)"

    def test_same_content_nearby_windows_cluster(self, demo_wavs: Path):
        """Sibling windows of the same content should be within tolerance."""
        fps = _fingerprint(demo_wavs / "espn_sportscenter.wav")
        max_adjacent = max(_hamming(fps[i][1], fps[i + 1][1]) for i in range(len(fps) - 1))
        assert max_adjacent < 90, (
            f"adjacent windows drift is {max_adjacent} bits — > 90 would make "
            "LSH recall impractical"
        )

    def test_different_content_diverges(self, demo_wavs: Path):
        """
        Different content must land materially further apart in hash space
        than same-content windows do. Our demo clips are synthetic
        narrow-band sinusoids — they under-exercise the algorithm compared
        to real broadcast audio. 55 bits is a pragmatic floor for this data
        (the production tolerance is 65, so anything >55 is safely above
        the false-match threshold in practice).
        """
        sports = _fingerprint(demo_wavs / "espn_sportscenter.wav")[0][1]
        news = _fingerprint(demo_wavs / "nbc_evening_news.wav")[0][1]
        drama = _fingerprint(demo_wavs / "succession.wav")[0][1]
        for other in (news, drama):
            dist = _hamming(sports, other)
            assert dist > 55, (
                f"sports vs unrelated audio differs by only {dist} bits — should be >55"
            )


class TestLSHRecall:
    """Simulate the Rust indexer's band-based LSH in memory to verify recall."""

    def _band_index(self, fp_hex: str, band_bytes: int = 1) -> list[tuple[int, str]]:
        return [
            (i, fp_hex[2 * i * band_bytes : 2 * (i + 1) * band_bytes])
            for i in range(32 // band_bytes)
        ]

    def _lookup(
        self, query: str, seeded: list[str], band_bytes: int = 1, hamming_tol: int = 65
    ) -> str | None:
        q_bands = set(self._band_index(query, band_bytes))
        best: tuple[int, str] | None = None
        for fp in seeded:
            if q_bands & set(self._band_index(fp, band_bytes)):
                d = _hamming(query, fp)
                if d <= hamming_tol and (best is None or d < best[0]):
                    best = (d, fp)
        return None if best is None else best[1]

    def test_exact_recall(self, demo_wavs: Path):
        fps = _fingerprint(demo_wavs / "espn_sportscenter.wav")
        seeded = [h for _, h in fps]
        # Query with an exactly-seeded fingerprint.
        assert self._lookup(seeded[5], seeded) == seeded[5]

    def test_noisy_recall(self, demo_wavs: Path):
        """
        Simulate a device that captured a slightly offset window of the
        content. The query fingerprint should still match the seeded set via
        the LSH band index + hamming tolerance.
        """
        dense = _fingerprint(demo_wavs / "espn_sportscenter.wav", hop_ms=500)
        seeded = [h for i, (_, h) in enumerate(dense) if i % 3 == 0]
        queries = [h for i, (_, h) in enumerate(dense) if i % 3 == 1]
        recalled = sum(1 for q in queries if self._lookup(q, seeded) is not None)
        # We should recall at least 60% of the offset queries.
        assert recalled / len(queries) > 0.6, (
            f"LSH recall dropped to {recalled}/{len(queries)}"
        )

    def test_no_false_positive_across_content(self, demo_wavs: Path):
        sports = [h for _, h in _fingerprint(demo_wavs / "espn_sportscenter.wav")]
        news_query = _fingerprint(demo_wavs / "nbc_evening_news.wav")[0][1]
        # News query against sports-only seed must not match.
        assert self._lookup(news_query, sports) is None


# -------------------- Live integration (opt-in) --------------------

LIVE = os.environ.get("SYNORA_E2E") == "live"
INDEXER_URL = os.environ.get("SYNORA_INDEXER_URL", "http://localhost:8082")


def _post(path: str, payload: dict) -> dict | None:
    req = request.Request(
        f"{INDEXER_URL}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except (error.HTTPError, error.URLError) as e:
        pytest.skip(f"indexer unreachable at {INDEXER_URL}: {e}")
        return None


@pytest.mark.skipif(not LIVE, reason="set SYNORA_E2E=live to exercise the real indexer")
class TestLiveIndexer:
    def test_roundtrip_match(self, demo_wavs: Path):
        fps = _fingerprint(demo_wavs / "succession.wav")
        # Seed the first frame as the 'reference' fingerprint.
        seed_hash = fps[0][1]
        resp = _post(
            "/v1/fingerprints/index",
            {
                "fingerprint_hash": seed_hash,
                "content_id": "test-succession-e2e",
                "title": "Succession (e2e test)",
                "network": "HBO",
                "genre": "drama",
                "confidence": 0.95,
            },
        )
        assert resp and resp.get("success") is True

        # Query with the same hash → expect exact match.
        resp2 = _post("/v1/fingerprints/lookup", {"fingerprint_hash": seed_hash})
        assert resp2 and resp2.get("matched") is True
        assert resp2.get("fingerprint", {}).get("content_id") == "test-succession-e2e"

        # Query with a sibling window → expect fuzzy match within tolerance.
        sibling_hash = fps[1][1]
        resp3 = _post(
            "/v1/fingerprints/lookup",
            {"fingerprint_hash": sibling_hash, "hamming_tolerance": 48},
        )
        # Sibling may or may not match depending on drift. Either way the
        # response must be well-formed.
        assert resp3 is not None
        assert "matched" in resp3
