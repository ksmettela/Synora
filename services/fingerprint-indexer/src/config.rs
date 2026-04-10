use anyhow::{anyhow, Result};
use std::env;

#[derive(Debug, Clone)]
pub struct Config {
    pub scylla_hosts: Vec<String>,
    pub kafka_bootstrap: String,
    pub kafka_group: String,
    pub http_port: u16,
    pub batch_size: usize,
    pub replication_factor: i32,
    pub hamming_threshold: u32,
}

impl Config {
    pub fn from_env() -> Result<Self> {
        let scylla_hosts = env::var("SCYLLA_HOSTS")
            .unwrap_or_else(|_| "127.0.0.1:9042".to_string())
            .split(',')
            .map(|s| s.trim().to_string())
            .collect();

        let kafka_bootstrap =
            env::var("KAFKA_BOOTSTRAP").unwrap_or_else(|_| "kafka:9092".to_string());

        let kafka_group = env::var("KAFKA_GROUP")
            .unwrap_or_else(|_| "fingerprint-indexer-group".to_string());

        let http_port = env::var("HTTP_PORT")
            .unwrap_or_else(|_| "8080".to_string())
            .parse::<u16>()
            .map_err(|e| anyhow\!("Invalid HTTP_PORT: {}", e))?;

        let batch_size = env::var("BATCH_SIZE")
            .unwrap_or_else(|_| "100".to_string())
            .parse::<usize>()
            .map_err(|e| anyhow\!("Invalid BATCH_SIZE: {}", e))?;

        let replication_factor = env::var("REPLICATION_FACTOR")
            .unwrap_or_else(|_| "1".to_string())
            .parse::<i32>()
            .map_err(|e| anyhow\!("Invalid REPLICATION_FACTOR: {}", e))?;

        let hamming_threshold = env::var("HAMMING_THRESHOLD")
            .unwrap_or_else(|_| "8".to_string())
            .parse::<u32>()
            .map_err(|e| anyhow\!("Invalid HAMMING_THRESHOLD: {}", e))?;

        Ok(Config {
            scylla_hosts,
            kafka_bootstrap,
            kafka_group,
            http_port,
            batch_size,
            replication_factor,
            hamming_threshold,
        })
    }
}
