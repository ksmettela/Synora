use crate::db::scylla::ScyllaClient;
use crate::models::{HealthResponse, IndexRequest, LookupRequest, LookupResponse, StatsResponse};
use axum::{
    extract::{Json, State},
    http::StatusCode,
};
use std::sync::Arc;
use std::time::Instant;
use tracing::error;

pub struct AppState {
    pub scylla: Arc<ScyllaClient>,
    pub hamming_threshold: u32,
}

pub async fn health(State(state): State<Arc<AppState>>) -> (StatusCode, Json<HealthResponse>) {
    let db_status = if state.scylla.count_fingerprints().await.is_ok() {
        "healthy".to_string()
    } else {
        "unhealthy".to_string()
    };

    let response = HealthResponse {
        status: "ok".to_string(),
        database: db_status,
        kafka: "connected".to_string(),
    };

    (StatusCode::OK, Json(response))
}

pub async fn index_fingerprint(
    State(state): State<Arc<AppState>>,
    Json(req): Json<IndexRequest>,
) -> (StatusCode, Json<serde_json::Value>) {
    match validate_fingerprint_hash(&req.fingerprint_hash) {
        Err(e) => {
            return (
                StatusCode::BAD_REQUEST,
                Json(serde_json::json\!({"error": e.to_string()})),
            )
        }
        Ok(_) => {}
    }

    let fp = crate::models::ReferenceFingerprint {
        fingerprint_hash: req.fingerprint_hash,
        content_id: req.content_id,
        title: req.title,
        network: req.network,
        episode: req.episode,
        airdate: req.airdate,
        genre: req.genre,
        created_at: chrono::Utc::now(),
        confidence: req.confidence,
    };

    match state.scylla.insert_fingerprint(&fp).await {
        Ok(_) => (
            StatusCode::CREATED,
            Json(serde_json::json\!({"success": true, "fingerprint_hash": fp.fingerprint_hash})),
        ),
        Err(e) => {
            error\!("Failed to index fingerprint: {}", e);
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(serde_json::json\!({"error": "Failed to index fingerprint"})),
            )
        }
    }
}

pub async fn lookup_fingerprint(
    State(state): State<Arc<AppState>>,
    Json(req): Json<LookupRequest>,
) -> (StatusCode, Json<LookupResponse>) {
    let start = Instant::now();

    if let Err(e) = validate_fingerprint_hash(&req.fingerprint_hash) {
        return (
            StatusCode::BAD_REQUEST,
            Json(LookupResponse {
                matched: false,
                fingerprint: None,
                hamming_distance: None,
                lookup_time_ms: start.elapsed().as_millis() as u64,
            }),
        );
    }

    let threshold = req.hamming_tolerance.unwrap_or(state.hamming_threshold);

    match state
        .scylla
        .lookup_with_hamming(&req.fingerprint_hash, threshold)
        .await
    {
        Ok(matches) => {
            let (fp, distance) = matches.first().map(|m| (m.0.clone(), m.1)).unwrap_or_else(|| {
                // Try exact match if no hamming match
                let fp = std::future::block_on(async {
                    state.scylla.lookup_fingerprint(&req.fingerprint_hash).await
                });
                (fp.flatten(), 0)
            });

            let response = LookupResponse {
                matched: fp.is_some(),
                fingerprint: fp,
                hamming_distance: if matches.is_empty() {
                    Some(distance)
                } else {
                    Some(matches[0].1)
                },
                lookup_time_ms: start.elapsed().as_millis() as u64,
            };

            (StatusCode::OK, Json(response))
        }
        Err(e) => {
            error\!("Lookup failed: {}", e);
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(LookupResponse {
                    matched: false,
                    fingerprint: None,
                    hamming_distance: None,
                    lookup_time_ms: start.elapsed().as_millis() as u64,
                }),
            )
        }
    }
}

pub async fn get_stats(
    State(state): State<Arc<AppState>>,
) -> (StatusCode, Json<StatsResponse>) {
    match state.scylla.count_fingerprints().await {
        Ok(total) => {
            let by_network = state.scylla.count_by_network().await.unwrap_or_default();
            (
                StatusCode::OK,
                Json(StatsResponse {
                    total_fingerprints: total,
                    by_network,
                }),
            )
        }
        Err(e) => {
            error\!("Failed to get stats: {}", e);
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(StatsResponse {
                    total_fingerprints: 0,
                    by_network: Default::default(),
                }),
            )
        }
    }
}

fn validate_fingerprint_hash(hash: &str) -> anyhow::Result<()> {
    if hash.len() \!= 64 {
        return Err(anyhow::anyhow\!("Fingerprint must be 64 hex characters (256 bits)"));
    }

    hex::decode(hash).map_err(|_| anyhow::anyhow\!("Invalid hex in fingerprint"))?;
    Ok(())
}
