use crate::config::Config;
use crate::models::{ReferenceFingerprint, FingerprintBand};
use anyhow::{anyhow, Result};
use chrono::Utc;
use scylla::load_balancing::{DcAwarePolicy, TokenAwarePolicy};
use scylla::transport::load_balancing::LoadBalancingPolicy;
use scylla::{Session, SessionBuilder};
use std::sync::Arc;
use tracing::{info, warn};

pub struct ScyllaClient {
    session: Arc<Session>,
}

impl ScyllaClient {
    pub async fn new(config: &Config) -> Result<Self> {
        let load_balancing = Arc::new(TokenAwarePolicy::new(Arc::new(
            DcAwarePolicy::new("us-east-1"),
        )));

        let session = SessionBuilder::new()
            .known_nodes(config.scylla_hosts.iter().map(|s| s.as_str()))
            .load_balancing(load_balancing)
            .build()
            .await
            .map_err(|e| anyhow\!("Failed to connect to ScyllaDB: {}", e))?;

        let client = ScyllaClient {
            session: Arc::new(session),
        };

        client.initialize_schema(config).await?;

        info\!("ScyllaDB client initialized");
        Ok(client)
    }

    async fn initialize_schema(&self, config: &Config) -> Result<()> {
        let replication = if config.replication_factor > 1 {
            format\!(
                "{{'class': 'NetworkTopologyStrategy', 'us-east-1': {}}}",
                config.replication_factor
            )
        } else {
            "{'class': 'SimpleStrategy', 'replication_factor': 1}".to_string()
        };

        let create_keyspace = format\!(
            "CREATE KEYSPACE IF NOT EXISTS acraas WITH replication = {}",
            replication
        );

        self.session
            .query(create_keyspace, &[])
            .await
            .map_err(|e| anyhow\!("Failed to create keyspace: {}", e))?;

        let create_table = r#"
            CREATE TABLE IF NOT EXISTS acraas.reference_fingerprints (
                fingerprint_hash text PRIMARY KEY,
                content_id text,
                title text,
                network text,
                episode text,
                airdate timestamp,
                genre text,
                created_at timestamp,
                confidence float
            )
        "#;

        self.session
            .query(create_table, &[])
            .await
            .map_err(|e| anyhow\!("Failed to create reference_fingerprints table: {}", e))?;

        let create_bands_table = r#"
            CREATE TABLE IF NOT EXISTS acraas.fingerprint_bands (
                band_index int,
                band_hash text,
                fingerprint_hash text,
                PRIMARY KEY ((band_index, band_hash), fingerprint_hash)
            )
        "#;

        self.session
            .query(create_bands_table, &[])
            .await
            .map_err(|e| anyhow\!("Failed to create fingerprint_bands table: {}", e))?;

        info\!("Schema initialized");
        Ok(())
    }

    pub async fn insert_fingerprint(&self, fp: &ReferenceFingerprint) -> Result<()> {
        let query = r#"
            INSERT INTO acraas.reference_fingerprints 
            (fingerprint_hash, content_id, title, network, episode, airdate, genre, created_at, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        "#;

        self.session
            .query(
                query,
                (
                    &fp.fingerprint_hash,
                    &fp.content_id,
                    &fp.title,
                    &fp.network,
                    &fp.episode,
                    fp.airdate,
                    &fp.genre,
                    Utc::now(),
                    fp.confidence,
                ),
            )
            .await
            .map_err(|e| anyhow\!("Failed to insert fingerprint: {}", e))?;

        self.insert_bands(&fp.fingerprint_hash).await?;
        Ok(())
    }

    async fn insert_bands(&self, fingerprint_hash: &str) -> Result<()> {
        let bytes = hex::decode(fingerprint_hash)
            .map_err(|e| anyhow\!("Invalid hex in fingerprint: {}", e))?;

        if bytes.len() \!= 32 {
            return Err(anyhow\!("Fingerprint must be 256 bits (32 bytes)"));
        }

        // 1-byte bands (32 bands total). The averaged-log-spectrum
        // fingerprint sees ~20% per-bit noise between same-content
        // fingerprints at small time offsets. Per-byte recall probability
        // with 1-byte bands is ~18%, giving ~99% LSH recall over 32 bands.
        // Larger band sizes drop recall below acceptable thresholds.
        for (band_idx, chunk) in bytes.chunks(1).enumerate() {
            let band_hash = hex::encode(chunk);
            let band = FingerprintBand {
                band_index: band_idx as i32,
                band_hash: band_hash.clone(),
                fingerprint_hash: fingerprint_hash.to_string(),
            };

            let query = r#"
                INSERT INTO acraas.fingerprint_bands
                (band_index, band_hash, fingerprint_hash)
                VALUES (?, ?, ?)
            "#;

            self.session
                .query(
                    query,
                    (band.band_index, &band.band_hash, &band.fingerprint_hash),
                )
                .await
                .map_err(|e| anyhow\!("Failed to insert band: {}", e))?;
        }

        Ok(())
    }

    pub async fn lookup_fingerprint(&self, fingerprint_hash: &str) -> Result<Option<ReferenceFingerprint>> {
        let query = r#"
            SELECT fingerprint_hash, content_id, title, network, episode, airdate, genre, created_at, confidence
            FROM acraas.reference_fingerprints
            WHERE fingerprint_hash = ?
        "#;

        let result = self.session
            .query(query, (fingerprint_hash,))
            .await
            .map_err(|e| anyhow\!("Failed to query fingerprint: {}", e))?;

        if let Some(rows) = result.rows {
            if let Some(row) = rows.first() {
                let fp = ReferenceFingerprint {
                    fingerprint_hash: row.get("fingerprint_hash")?,
                    content_id: row.get("content_id")?,
                    title: row.get("title")?,
                    network: row.get("network")?,
                    episode: row.get("episode").ok(),
                    airdate: row.get("airdate").ok(),
                    genre: row.get("genre")?,
                    created_at: row.get("created_at")?,
                    confidence: row.get("confidence")?,
                };
                return Ok(Some(fp));
            }
        }

        Ok(None)
    }

    pub async fn lookup_with_hamming(
        &self,
        fingerprint_hash: &str,
        hamming_threshold: u32,
    ) -> Result<Vec<(ReferenceFingerprint, u32)>> {
        let bytes = hex::decode(fingerprint_hash)
            .map_err(|e| anyhow\!("Invalid hex in fingerprint: {}", e))?;

        if bytes.len() \!= 32 {
            return Err(anyhow\!("Fingerprint must be 256 bits (32 bytes)"));
        }

        let mut candidates = std::collections::HashSet::new();

        for (band_idx, chunk) in bytes.chunks(1).enumerate() {
            let band_hash = hex::encode(chunk);
            let query = r#"
                SELECT fingerprint_hash FROM acraas.fingerprint_bands
                WHERE band_index = ? AND band_hash = ?
            "#;

            if let Ok(result) = self.session.query(query, (band_idx as i32, &band_hash)).await {
                if let Some(rows) = result.rows {
                    for row in rows {
                        if let Ok(hash) = row.get::<String>("fingerprint_hash") {
                            candidates.insert(hash);
                        }
                    }
                }
            }
        }

        let mut matches = Vec::new();

        for candidate_hash in candidates {
            let distance = hamming_distance(fingerprint_hash, &candidate_hash)?;

            if distance <= hamming_threshold {
                if let Ok(Some(fp)) = self.lookup_fingerprint(&candidate_hash).await {
                    matches.push((fp, distance));
                }
            }
        }

        matches.sort_by_key(|(_fp, dist)| *dist);
        Ok(matches)
    }

    pub async fn bulk_insert(&self, fingerprints: Vec<ReferenceFingerprint>) -> Result<()> {
        for fp in fingerprints {
            self.insert_fingerprint(&fp).await?;
        }
        Ok(())
    }

    pub async fn count_fingerprints(&self) -> Result<i64> {
        let query = "SELECT COUNT(*) as count FROM acraas.reference_fingerprints";
        let result = self.session
            .query(query, &[])
            .await
            .map_err(|e| anyhow\!("Failed to count fingerprints: {}", e))?;

        if let Some(rows) = result.rows {
            if let Some(row) = rows.first() {
                let count = row.get::<i64>("count")?;
                return Ok(count);
            }
        }

        Ok(0)
    }

    pub async fn count_by_network(&self) -> Result<std::collections::HashMap<String, i64>> {
        let query = "SELECT network, COUNT(*) as count FROM acraas.reference_fingerprints GROUP BY network";
        let result = self.session
            .query(query, &[])
            .await
            .map_err(|e| anyhow\!("Failed to count by network: {}", e))?;

        let mut counts = std::collections::HashMap::new();

        if let Some(rows) = result.rows {
            for row in rows {
                let network: String = row.get("network")?;
                let count: i64 = row.get("count")?;
                counts.insert(network, count);
            }
        }

        Ok(counts)
    }
}

fn hamming_distance(hash1: &str, hash2: &str) -> Result<u32> {
    let bytes1 = hex::decode(hash1)
        .map_err(|e| anyhow\!("Invalid hex in hash1: {}", e))?;
    let bytes2 = hex::decode(hash2)
        .map_err(|e| anyhow\!("Invalid hex in hash2: {}", e))?;

    if bytes1.len() \!= bytes2.len() {
        return Err(anyhow\!("Hashes must be same length"));
    }

    let distance = bytes1
        .iter()
        .zip(bytes2.iter())
        .map(|(b1, b2)| (b1 ^ b2).count_ones())
        .sum();

    Ok(distance)
}
