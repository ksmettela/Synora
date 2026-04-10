use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReferenceFingerprint {
    pub fingerprint_hash: String,
    pub content_id: String,
    pub title: String,
    pub network: String,
    pub episode: Option<String>,
    pub airdate: Option<DateTime<Utc>>,
    pub genre: String,
    pub created_at: DateTime<Utc>,
    pub confidence: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FingerprintBand {
    pub band_index: i32,
    pub band_hash: String,
    pub fingerprint_hash: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LookupRequest {
    pub fingerprint_hash: String,
    pub hamming_tolerance: Option<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LookupResponse {
    pub matched: bool,
    pub fingerprint: Option<ReferenceFingerprint>,
    pub hamming_distance: Option<u32>,
    pub lookup_time_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IndexRequest {
    pub fingerprint_hash: String,
    pub content_id: String,
    pub title: String,
    pub network: String,
    pub episode: Option<String>,
    pub airdate: Option<DateTime<Utc>>,
    pub genre: String,
    pub confidence: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StatsResponse {
    pub total_fingerprints: i64,
    pub by_network: std::collections::HashMap<String, i64>,
}

#[derive(Debug, Clone)]
pub struct HealthResponse {
    pub status: String,
    pub database: String,
    pub kafka: String,
}
