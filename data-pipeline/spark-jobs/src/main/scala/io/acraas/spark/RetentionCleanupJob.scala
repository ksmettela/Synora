package io.acraas.spark

import org.apache.spark.sql.{SparkSession, DataFrame}
import org.apache.spark.sql.functions._
import java.time.LocalDate

object RetentionCleanupJob {

  def main(args: Array[String]): Unit = {
    val spark = SparkSession.builder()
      .appName("ACRaaS Data Retention Cleanup")
      .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
      .config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog")
      .config("spark.sql.catalog.iceberg.type", "hive")
      .config("spark.sql.catalog.iceberg.warehouse", System.getenv().getOrDefault("ICEBERG_WAREHOUSE", "s3://acraas-warehouse/warehouse"))
      .getOrCreate()

    spark.sparkContext.setLogLevel("INFO")

    val icebergWarehouse = System.getenv().getOrDefault("ICEBERG_WAREHOUSE", "s3://acraas-warehouse/warehouse")
    val viewershipTablePath = s"$icebergWarehouse/acraas/viewership"
    val aggregatesTablePath = s"$icebergWarehouse/acraas/household_aggregates"
    val auditTablePath = s"$icebergWarehouse/acraas/deletion_audit"

    try {
      val deletionResults = scala.collection.mutable.Map[String, Long]()

      println("Starting retention cleanup job...")

      deletionResults("viewership_deleted_count") = cleanupViewership(spark, viewershipTablePath)

      deletionResults("aggregates_archived_count") = archiveAggregates(spark, aggregatesTablePath)

      println("Logging deletion audit...")
      logDeletionAudit(spark, auditTablePath, deletionResults)

      println(s"Retention cleanup completed: $deletionResults")

    } catch {
      case e: Exception =>
        println(s"Error during retention cleanup: ${e.getMessage}")
        e.printStackTrace()
        throw e
    } finally {
      spark.stop()
    }
  }

  private def cleanupViewership(spark: SparkSession, tableNs: String): Long = {
    val cutoffDate = LocalDate.now().minusDays(90).toString
    
    try {
      val countBefore = spark.sql(s"SELECT COUNT(*) as cnt FROM iceberg.`$tableNs`").collect()(0).getLong(0)
      
      spark.sql(s"""
        DELETE FROM iceberg.`$tableNs`
        WHERE watch_date < '$cutoffDate'
      """)
      
      val countAfter = spark.sql(s"SELECT COUNT(*) as cnt FROM iceberg.`$tableNs`").collect()(0).getLong(0)
      val deletedCount = countBefore - countAfter
      
      println(s"Deleted $deletedCount viewership records older than $cutoffDate")
      deletedCount
    } catch {
      case e: Exception =>
        println(s"Error cleaning up viewership data: ${e.getMessage}")
        0
    }
  }

  private def archiveAggregates(spark: SparkSession, tableNs: String): Long = {
    val cutoffDate = LocalDate.now().minusDays(365).toString
    val archiveBucket = System.getenv().getOrDefault("ARCHIVE_S3_BUCKET", "acraas-archive")
    
    try {
      val aggregatesToArchive = spark.sql(s"""
        SELECT *
        FROM iceberg.`$tableNs`
        WHERE aggregated_at < '$cutoffDate'
      """)
      
      val archivedCount = aggregatesToArchive.count()
      
      if (archivedCount > 0) {
        val archivePath = s"s3://$archiveBucket/household_aggregates_archive/${LocalDate.now()}"
        
        aggregatesToArchive.write.parquet(archivePath)
        
        spark.sql(s"""
          DELETE FROM iceberg.`$tableNs`
          WHERE aggregated_at < '$cutoffDate'
        """)
        
        println(s"Archived $archivedCount household aggregates older than $cutoffDate to $archivePath")
      }
      
      archivedCount
    } catch {
      case e: Exception =>
        println(s"Error archiving aggregates: ${e.getMessage}")
        0
    }
  }

  private def logDeletionAudit(spark: SparkSession, auditTable: String, results: scala.collection.mutable.Map[String, Long]): Unit = {
    try {
      val auditDf = spark.createDataFrame(
        Seq((
          java.time.LocalDateTime.now().toString,
          results.getOrElse("viewership_deleted_count", 0L),
          results.getOrElse("aggregates_archived_count", 0L),
          "SUCCESS"
        ))
      ).toDF("execution_time", "viewership_deleted_count", "aggregates_archived_count", "status")
      
      auditDf.write.format("iceberg")
        .mode("append")
        .option("mergeSchema", "true")
        .save(auditTable)
      
      println(s"Audit logged: ${results}")
    } catch {
      case e: Exception =>
        println(s"Error logging deletion audit: ${e.getMessage}")
    }
  }
}
