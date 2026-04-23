#!/usr/bin/env python3
"""
Seed the ScyllaDB reference fingerprint index from a content catalog.

Input: a JSON manifest describing WAV files + their content metadata.
Process: shells out to `fingerprint_cli` for each file (1.5s hop, 3s window)
and POSTs each resulting fingerprint to the fingerprint-indexer service.

Usage:
    python3 seed_reference_catalog.py \\
        --catalog catalogs/demo.json \\
        --fingerprint-cli /path/to/fingerprint_cli \\
        --indexer-url http://localhost:8082

The shell-out model keeps the device-side algorithm (C++) as the single
source of truth — Python never re-implements the fingerprint, it just moves
bytes.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable
from urllib import request, error


def fingerprint_wav(cli_path: str, wav_path: str, window_ms: int, hop_ms: int) -> Iterable[tuple[int, str]]:
    """Yield (start_ms, fingerprint_hex) pairs by shelling out to fingerprint_cli."""
    proc = subprocess.run(
        [cli_path, wav_path, "--window-ms", str(window_ms), "--hop-ms", str(hop_ms)],
        check=True,
        capture_output=True,
        text=True,
    )
    for line in proc.stdout.strip().splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            yield int(parts[0]), parts[1].strip()


def post_fingerprint(indexer_url: str, fingerprint_hash: str, entry: dict, start_ms: int) -> bool:
    """POST one fingerprint to the indexer. Returns True on success."""
    payload = {
        "fingerprint_hash": fingerprint_hash,
        "content_id": f"{entry['content_id']}:{start_ms}",
        "title": entry["title"],
        "network": entry.get("network", "unknown"),
        "genre": entry.get("genre", "unknown"),
        "episode": entry.get("episode"),
        "airdate": entry.get("airdate"),
        "confidence": entry.get("confidence", 0.95),
    }
    data = json.dumps({k: v for k, v in payload.items() if v is not None}).encode()
    req = request.Request(
        f"{indexer_url.rstrip('/')}/v1/fingerprints/index",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=5) as resp:
            return resp.status in (200, 201)
    except error.HTTPError as e:
        sys.stderr.write(f"  HTTP {e.code}: {e.read().decode(errors='replace')[:200]}\n")
        return False
    except error.URLError as e:
        sys.stderr.write(f"  network error: {e}\n")
        return False


def seed(catalog_path: Path, cli_path: str, indexer_url: str, window_ms: int, hop_ms: int) -> int:
    with catalog_path.open() as f:
        catalog = json.load(f)

    base_dir = catalog_path.parent
    total_inserted = 0
    total_failed = 0

    for entry in catalog.get("items", []):
        wav = entry["wav"]
        wav_path = str((base_dir / wav).resolve()) if not os.path.isabs(wav) else wav
        if not os.path.exists(wav_path):
            sys.stderr.write(f"skip (missing): {wav_path}\n")
            continue

        print(f"-> {entry['title']} ({wav_path})", flush=True)
        for start_ms, fp_hex in fingerprint_wav(cli_path, wav_path, window_ms, hop_ms):
            ok = post_fingerprint(indexer_url, fp_hex, entry, start_ms)
            if ok:
                total_inserted += 1
            else:
                total_failed += 1
                sys.stderr.write(f"  failed at {start_ms}ms\n")

    print(f"\nSeed complete: {total_inserted} inserted, {total_failed} failed")
    return 0 if total_failed == 0 else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--catalog", type=Path, required=True)
    ap.add_argument("--fingerprint-cli", required=True)
    ap.add_argument("--indexer-url", default="http://localhost:8082")
    ap.add_argument("--window-ms", type=int, default=3000)
    ap.add_argument("--hop-ms", type=int, default=1500)
    args = ap.parse_args()

    return seed(args.catalog, args.fingerprint_cli, args.indexer_url,
                args.window_ms, args.hop_ms)


if __name__ == "__main__":
    sys.exit(main())
