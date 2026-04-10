package io.acraas.spark

import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions._
import java.time.LocalDate

object IcebergMaintenanceJob {

  def main(args: Array[String]): Unit = {
    val spark = SparkSession.builder()
      .appName("ACRaaS Iceberg Maintenance")
      .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
      .config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog")
      .config("spark.sql.catalog.iceberg.type", "hive")
      .config("spark.sql.catalog.iceberg.warehouse", System.getenv().getOrDefault("ICEBERG_WAREHOUSE", "s3://acraas-warehouse/warehouse"))
      .getOrCreate()

    spark.sparkContext.setLogLevel("INFO")

    val icebergWarehouse = System.getenv().getOrDefault("ICEBERG_WAREHOUSE", "s3://acraas-warehouse/warehouse")

    try {
      println("Starting Iceberg maintenance tasks...")

      val tables = Seq(
        s"$icebergWarehouse/acraas/viewership",
        s"$icebergWarehouse/acraas/household_aggregates",
        s"$icebergWarehouse/acraas/deletion_audit"
      )

      for (table <- tables) {
        println(s"Processing table: $table")
        
        try {
          expireSnapshots(spark, table)
        } catch {
          case e: Exception =>
            println(s"Error expiring snapshots for $table: ${e.getMessage}")
        }

        try {
          removeOrphanFiles(spark, table)
        } catch {
          case e: Exception =>
            println(s"Error removing orphan files for $table: ${e.getMessage}")
        }

        try {
          rewriteDataFiles(spark, table)
        } catch {
          case e: Exception =>
            println(s"Error rewriting data files for $table: ${e.getMessage}")
        }
      }

      println("Iceberg maintenance completed successfully")

    } catch {
      case e: Exception =>
        println(s"Error during Iceberg maintenance: ${e.getMessage}")
        e.printStackTrace()
        throw e
    } finally {
      spark.stop()
    }
  }

  private def expireSnapshots(spark: SparkSession, tableName: String): Unit = {
    val snapshotRetentionDays = System.getenv().getOrDefault("SNAPSHOT_RETENTION_DAYS", "7").toInt
    
    try {
      println(s"Expiring snapshots older than $snapshotRetentionDays days for $tableName")
      
      spark.sql(s"""
        CALL iceberg.system.expire_snapshots(
          table => 'iceberg.`$tableName`',
          older_than => CAST(${snapshotRetentionDays}L * 24 * 60 * 60 * 1000 as BIGINT),
          retain_last => 5
        )
      """)
      
      println(s"Successfully expired snapshots for $tableName")
    } catch {
      case e: Exception =>
        println(s"Failed to expire snapshots for $tableName: ${e.getMessage}")
    }
  }

  private def removeOrphanFiles(spark: SparkSession, tableName: String): Unit = {
    try {
      println(s"Removing orphan files for $tableName")
      
      spark.sql(s"""
        CALL iceberg.system.remove_orphan_files(
          table => 'iceberg.`$tableName`',
          older_than => CAST(7 * 24 * 60 * 60 * 1000 as BIGINT),
          dry_run => false
        )
      """)
      
      println(s"Successfully removed orphan files for $tableName")
    } catch {
      case e: Exception =>
        println(s"Failed to remove orphan files for $tableName: ${e.getMessage}")
    }
  }

  private def rewriteDataFiles(spark: SparkSession, tableName: String): Unit = {
    try {
      println(s"Rewriting small data files for $tableName")
      
      spark.sql(s"""
        CALL iceberg.system.rewrite_data_files(
          table => 'iceberg.`$tableName`',
          strategy => 'binpack',
          sort_order => 'zorder',
          options => map(
            'min-input-files', '5',
            'target-file-size-bytes', '134217728'
          )
        )
      """)
      
      println(s"Successfully rewrote data files for $tableName")
    } catch {
      case e: Exception =>
        println(s"Failed to rewrite data files for $tableName: ${e.getMessage}")
    }
  }
}
