mod config;
mod db;
mod http;
mod kafka;
mod models;

use axum::{
    routing::{get, post},
    Router,
};
use config::Config;
use db::scylla::ScyllaClient;
use http::handlers::AppState;
use std::sync::Arc;
use tokio::task;
use tower_http::trace::TraceLayer;
use tracing::{error, info};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    dotenv::dotenv().ok();
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::from_default_env()
                .add_directive("fingerprint_indexer=info".parse()?),
        )
        .json()
        .init();

    let config = Config::from_env()?;
    info!("Configuration loaded: {:?}", config);

    let scylla = Arc::new(ScyllaClient::new(&config).await?);
    info!("ScyllaDB client initialized");

    let app_state = Arc::new(AppState {
        scylla: scylla.clone(),
        hamming_threshold: config.hamming_threshold,
    });

    let kafka_consumer =
        kafka::consumer::KafkaConsumer::new(&config, scylla.clone()).await?;
    info!("Kafka consumer initialized");

    let kafka_handle = task::spawn(async move {
        if let Err(e) = kafka_consumer.run().await {
            error!("Kafka consumer error: {}", e);
        }
    });

    let app = Router::new()
        .route("/health", get(http::handlers::health))
        .route(
            "/v1/fingerprints/index",
            post(http::handlers::index_fingerprint),
        )
        .route(
            "/v1/fingerprints/lookup",
            post(http::handlers::lookup_fingerprint),
        )
        .route("/v1/fingerprints/stats", get(http::handlers::get_stats))
        .with_state(app_state)
        .layer(TraceLayer::new_for_http());

    let listener = tokio::net::TcpListener::bind(format!("0.0.0.0:{}", config.http_port))
        .await?;

    info!("HTTP server listening on 0.0.0.0:{}", config.http_port);

    let server_handle = task::spawn(async move {
        if let Err(e) = axum::serve(listener, app).await {
            error!("Server error: {}", e);
        }
    });

    tokio::select! {
        _ = server_handle => {
            info!("HTTP server stopped");
        }
        _ = kafka_handle => {
            info!("Kafka consumer stopped");
        }
    }

    Ok(())
}
