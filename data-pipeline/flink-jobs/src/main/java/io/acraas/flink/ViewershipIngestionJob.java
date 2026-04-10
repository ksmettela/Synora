package io.acraas.flink;

import io.acraas.flink.enrichment.HouseholdEnricher;
import io.acraas.flink.model.EnrichedViewershipEvent;
import io.acraas.flink.model.ViewershipEvent;
import io.acraas.flink.serde.ViewershipEventDeserializer;
import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Properties;

public class ViewershipIngestionJob {
    private static final Logger LOG = LoggerFactory.getLogger(ViewershipIngestionJob.class);

    public static void main(String[] args) throws Exception {
        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

        LOG.info("Starting ACRaaS Viewership Iceberg Ingestion Job");

        env.enableCheckpointing(60_000);
        env.getCheckpointConfig().setCheckpointingMode(
            org.apache.flink.streaming.api.CheckpointingMode.EXACTLY_ONCE
        );

        String kafkaBrokers = System.getenv().getOrDefault("KAFKA_BROKERS", "kafka:9092");
        String s3Bucket = System.getenv().getOrDefault("S3_BUCKET", "acraas-warehouse");
        String icebergTablePath = System.getenv().getOrDefault("ICEBERG_TABLE_PATH", "s3://acraas-warehouse/acraas/viewership");

        LOG.info("Configuration: kafkaBrokers={}, s3Bucket={}, icebergTablePath={}",
                kafkaBrokers, s3Bucket, icebergTablePath);

        KafkaSource<ViewershipEvent> source = KafkaSource.<ViewershipEvent>builder()
            .setBootstrapServers(kafkaBrokers)
            .setTopics("matched.viewership")
            .setGroupId("flink-iceberg-ingestor")
            .setStartingOffsets(OffsetsInitializer.committedOffsets(OffsetsInitializer.OffsetResetStrategy.EARLIEST))
            .setValueOnlyDeserializer(new ViewershipEventDeserializer())
            .setProperty("security.protocol", System.getenv().getOrDefault("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"))
            .build();

        DataStream<ViewershipEvent> stream = env.fromSource(
            source,
            WatermarkStrategy.noWatermarks(),
            "Kafka Source - matched.viewership"
        );

        LOG.info("Kafka source initialized");

        DataStream<EnrichedViewershipEvent> enriched = stream
            .map(new HouseholdEnricher())
            .name("Household Enricher");

        LOG.info("Enrichment stage configured");

        enriched.sinkTo(io.acraas.flink.iceberg.IcebergSinkBuilder.buildSink(icebergTablePath, s3Bucket))
            .name("Iceberg Sink - viewership");

        LOG.info("Iceberg sink configured");

        env.execute("ACRaaS Viewership Iceberg Ingestion");
    }
}
