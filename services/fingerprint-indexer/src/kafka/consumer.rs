use crate::config::Config;
use crate::db::scylla::ScyllaClient;
use crate::models::ReferenceFingerprint;
use anyhow::{anyhow, Result};
use rdkafka::config::ClientConfig;
use rdkafka::consumer::{Consumer, StreamConsumer};
use rdkafka::message::Message;
use std::sync::Arc;
use tracing::{error, info, warn};

pub struct KafkaConsumer {
    consumer: StreamConsumer,
    scylla: Arc<ScyllaClient>,
    batch_size: usize,
}

impl KafkaConsumer {
    pub async fn new(config: &Config, scylla: Arc<ScyllaClient>) -> Result<Self> {
        let consumer: StreamConsumer = ClientConfig::new()
            .set("bootstrap.servers", &config.kafka_bootstrap)
            .set("group.id", &config.kafka_group)
            .set("auto.offset.reset", "earliest")
            .set("enable.auto.commit", "true")
            .set("session.timeout.ms", "30000")
            .create()
            .map_err(|e| anyhow!("Failed to create Kafka consumer: {}", e))?;

        consumer
            .subscribe(&["reference.content"])
            .map_err(|e| anyhow!("Failed to subscribe to topic: {}", e))?;

        info!("Kafka consumer created and subscribed to reference.content");

        Ok(KafkaConsumer {
            consumer,
            scylla,
            batch_size: config.batch_size,
        })
    }

    pub async fn run(&self) -> Result<()> {
        info!("Starting Kafka consumer loop");
        let mut batch = Vec::new();

        loop {
            match self.consumer.recv().await {
                Ok(msg) => {
                    let payload = match msg.payload() {
                        Some(data) => data,
                        None => {
                            warn!("Received empty Kafka message");
                            continue;
                        }
                    };

                    match serde_json::from_slice::<serde_json::Value>(payload) {
                        Ok(value) => {
                            if let Ok(fp) = self.parse_fingerprint_event(&value) {
                                batch.push(fp);

                                if batch.len() >= self.batch_size {
                                    if let Err(e) = self.scylla.bulk_insert(batch.clone()).await {
                                        error!("Failed to insert batch: {}", e);
                                    } else {
                                        info!("Inserted batch of {} fingerprints", batch.len());
                                    }
                                    batch.clear();
                                }
                            }
                        }
                        Err(e) => {
                            warn!("Failed to parse Kafka message: {}", e);
                        }
                    }
                }
                Err(e) => {
                    error!("Kafka consumer error: {}", e);
                    tokio::time::sleep(tokio::time::Duration::from_secs(5)).await;
                }
            }
        }
    }

    fn parse_fingerprint_event(&self, value: &serde_json::Value) -> Result<ReferenceFingerprint> {
        let obj = value
            .as_object()
            .ok_or_else(|| anyhow!("Invalid JSON object"))?;

        let fingerprint_hash = obj
            .get("fingerprint_hash")
            .and_then(|v| v.as_str())
            .ok_or_else(|| anyhow!("Missing fingerprint_hash"))?
            .to_string();

        let content_id = obj
            .get("content_id")
            .and_then(|v| v.as_str())
            .ok_or_else(|| anyhow!("Missing content_id"))?
            .to_string();

        let title = obj
            .get("title")
            .and_then(|v| v.as_str())
            .ok_or_else(|| anyhow!("Missing title"))?
            .to_string();

        let network = obj
            .get("network")
            .and_then(|v| v.as_str())
            .ok_or_else(|| anyhow!("Missing network"))?
            .to_string();

        let genre = obj
            .get("genre")
            .and_then(|v| v.as_str())
            .unwrap_or("unknown")
            .to_string();

        let episode = obj
            .get("episode")
            .and_then(|v| v.as_str())
            .map(|s| s.to_string());

        let airdate = obj
            .get("airdate")
            .and_then(|v| v.as_str())
            .and_then(|s| chrono::DateTime::parse_from_rfc3339(s).ok())
            .map(|dt| dt.with_timezone(&chrono::Utc));

        let confidence = obj
            .get("confidence")
            .and_then(|v| v.as_f64())
            .unwrap_or(1.0) as f32;

        Ok(ReferenceFingerprint {
            fingerprint_hash,
            content_id,
            title,
            network,
            episode,
            airdate,
            genre,
            created_at: chrono::Utc::now(),
            confidence,
        })
    }
}
