package io.acraas.flink.iceberg;

import io.acraas.flink.model.EnrichedViewershipEvent;
import org.apache.flink.streaming.api.connector.sink2.Sink;
import org.apache.iceberg.flink.sink.FlinkSink;
import org.apache.iceberg.Schema;
import org.apache.iceberg.types.Types;

import java.util.HashMap;
import java.util.Map;

public class IcebergSinkBuilder {

    public static Sink<EnrichedViewershipEvent> buildSink(String icebergTablePath, String s3Bucket) {
        Map<String, String> properties = new HashMap<>();

        properties.put("warehouse", "s3://" + s3Bucket + "/warehouse");
        properties.put("io-impl", "org.apache.iceberg.aws.s3.S3FileIO");
        properties.put("s3.endpoint", "http://minio:9000");
        properties.put("s3.access-key-id", System.getenv("AWS_ACCESS_KEY_ID"));
        properties.put("s3.secret-access-key", System.getenv("AWS_SECRET_ACCESS_KEY"));

        properties.put("write.format.default", "parquet");
        properties.put("write.target-file-size-bytes", String.valueOf(128 * 1024 * 1024));

        Schema schema = new Schema(
            Types.NestedField.required(1, "device_id", Types.StringType.get()),
            Types.NestedField.optional(2, "household_id", Types.StringType.get()),
            Types.NestedField.required(3, "content_id", Types.StringType.get()),
            Types.NestedField.optional(4, "title", Types.StringType.get()),
            Types.NestedField.optional(5, "network", Types.StringType.get()),
            Types.NestedField.optional(6, "genre", Types.StringType.get()),
            Types.NestedField.optional(7, "watch_date", Types.StringType.get()),
            Types.NestedField.optional(8, "watch_hour", Types.IntegerType.get()),
            Types.NestedField.optional(9, "duration_minutes", Types.IntegerType.get()),
            Types.NestedField.optional(10, "dma_code", Types.StringType.get()),
            Types.NestedField.optional(11, "zip_code", Types.StringType.get()),
            Types.NestedField.optional(12, "manufacturer", Types.StringType.get()),
            Types.NestedField.optional(13, "model", Types.StringType.get()),
            Types.NestedField.optional(14, "match_confidence", Types.FloatType.get()),
            Types.NestedField.optional(15, "watch_start_utc", Types.LongType.get()),
            Types.NestedField.optional(16, "duration_sec", Types.IntegerType.get()),
            Types.NestedField.optional(17, "ip_address", Types.StringType.get()),
            Types.NestedField.required(18, "ingest_timestamp", Types.TimestampType.withZone())
        );

        return FlinkSink.forRowData()
            .table(icebergTablePath)
            .tableLoader(createTableLoader(icebergTablePath, properties))
            .writeParquet()
            .withPartitionColumns("watch_date", "network", "genre")
            .append()
            .build();
    }

    private static org.apache.iceberg.flink.TableLoader createTableLoader(String tablePath, Map<String, String> properties) {
        return org.apache.iceberg.flink.TableLoader.fromHadoopTable(tablePath, createHadoopConf(properties));
    }

    private static org.apache.hadoop.conf.Configuration createHadoopConf(Map<String, String> properties) {
        org.apache.hadoop.conf.Configuration conf = new org.apache.hadoop.conf.Configuration();
        properties.forEach(conf::set);
        return conf;
    }
}
