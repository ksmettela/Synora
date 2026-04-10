package io.acraas.spark

import org.apache.spark.sql.{SparkSession, DataFrame, Window}
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._
import scala.collection.mutable
import java.time.LocalDate

object HouseholdAggregationJob {
  
  def main(args: Array[String]): Unit = {
    val spark = SparkSession.builder()
      .appName("Synora Household Aggregation")
      .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
      .config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog")
      .config("spark.sql.catalog.iceberg.type", "hive")
      .config("spark.sql.catalog.iceberg.warehouse", System.getenv().getOrDefault("ICEBERG_WAREHOUSE", "s3://acraas-warehouse/warehouse"))
      .getOrCreate()

    spark.sparkContext.setLogLevel("INFO")

    val icebergWarehouse = System.getenv().getOrDefault("ICEBERG_WAREHOUSE", "s3://acraas-warehouse/warehouse")
    val viewershipTablePath = s"$icebergWarehouse/acraas/viewership"
    val aggregatesTablePath = s"$icebergWarehouse/acraas/household_aggregates"

    try {
      println("Reading viewership data from Iceberg...")
      val viewershipDf = spark.read.format("iceberg")
        .option("startSnapshotId", getSnapshotIdFromDaysAgo(spark, viewershipTablePath, 7))
        .load(viewershipTablePath)
        .filter(col("watch_date") >= lit(LocalDate.now().minusDays(7).toString))

      viewershipDf.show(5)

      println("Computing genre affinity scores...")
      val genreAffinityDf = computeGenreAffinity(viewershipDf)
      genreAffinityDf.show(5)

      println("Computing daypart patterns...")
      val daypartPatternsDf = computeDaypartPatterns(viewershipDf)
      daypartPatternsDf.show(5)

      println("Computing brand affinity signals...")
      val brandAffinityDf = computeBrandAffinity(viewershipDf)

      println("Joining aggregates...")
      val householdAggregateDf = genreAffinityDf
        .join(daypartPatternsDf, Seq("household_id"), "inner")
        .join(brandAffinityDf, Seq("household_id"), "left")
        .withColumn("aggregated_at", current_timestamp())

      println("Writing household aggregates to Iceberg...")
      householdAggregateDf.write.format("iceberg")
        .mode("overwrite")
        .option("mergeSchema", "true")
        .save(aggregatesTablePath)

      println("Household aggregation job completed successfully")

    } catch {
      case e: Exception =>
        println(s"Error during household aggregation: ${e.getMessage}")
        e.printStackTrace()
        throw e
    } finally {
      spark.stop()
    }
  }

  private def computeGenreAffinity(viewershipDf: DataFrame): DataFrame = {
    viewershipDf
      .filter(col("genre").isNotNull)
      .groupBy("household_id", "genre")
      .agg(
        (sum(col("duration_minutes")) / 60).alias("hours_watched"),
        count(lit(1)).alias("watch_count")
      )
      .groupBy("household_id")
      .agg(
        collect_list(
          struct(
            col("genre"),
            col("hours_watched"),
            col("watch_count")
          )
        ).alias("genre_affinity_list")
      )
      .withColumn("genre_affinity_scores", 
        when(col("genre_affinity_list").isNotNull,
          expr("""
            transform(
              genre_affinity_list,
              x -> struct(
                x.genre as genre,
                cast((x.hours_watched / greatest(sum(x.hours_watched) over (), 1)) * 100 as int) as score
              )
            )
          """)
        ).otherwise(array())
      )
      .select("household_id", "genre_affinity_scores")
  }

  private def computeDaypartPatterns(viewershipDf: DataFrame): DataFrame = {
    val daypartDf = viewershipDf
      .filter(col("watch_hour").isNotNull)
      .withColumn("daypart",
        when(col("watch_hour") >= 6 && col("watch_hour") < 12, "morning")
          .when(col("watch_hour") >= 12 && col("watch_hour") < 18, "afternoon")
          .when(col("watch_hour") >= 18 && col("watch_hour") < 23, "primetime")
          .otherwise("latenight")
      )

    daypartDf
      .groupBy("household_id", "daypart")
      .agg(count(lit(1)).alias("watch_count"))
      .groupBy("household_id")
      .agg(
        collect_list(
          struct(
            col("daypart"),
            col("watch_count")
          )
        ).alias("daypart_list")
      )
      .withColumn("daypart_patterns",
        when(col("daypart_list").isNotNull,
          expr("""
            transform(
              daypart_list,
              x -> struct(
                x.daypart as daypart,
                cast((x.watch_count / greatest(sum(x.watch_count) over (), 1)) * 100 as int) as percentage
              )
            )
          """)
        ).otherwise(array())
      )
      .select("household_id", "daypart_patterns")
  }

  private def computeBrandAffinity(viewershipDf: DataFrame): DataFrame = {
    viewershipDf
      .select("household_id")
      .distinct()
      .withColumn("brand_affinity_signals", array())
      .withColumn("affinity_note", lit("TODO: Requires ad catalog join for real implementation"))
  }

  private def getSnapshotIdFromDaysAgo(spark: SparkSession, tablePath: String, daysAgo: Int): Long = {
    val sql = s"""
      SELECT snapshot_id 
      FROM iceberg.system.snapshots
      WHERE table_name = '${tablePath.split("/").last}'
      ORDER BY committed_at DESC
      LIMIT 1
    """
    try {
      spark.sql(sql).collect()(0).getLong(0)
    } catch {
      case _: Exception =>
        Long.MaxValue
    }
  }
}
