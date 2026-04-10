ThisBuild / name := "acraas-spark-jobs"
ThisBuild / version := "1.0.0"
ThisBuild / scalaVersion := "2.12.18"
ThisBuild / organization := "io.acraas"

scalacOptions ++= Seq(
  "-target:jvm-1.11",
  "-deprecation",
  "-feature",
  "-unchecked",
  "-Xlint",
  "-Ywarn-unused-import"
)

lazy val sparkVersion = "3.5.0"
lazy val icebergVersion = "1.4.0"

libraryDependencies ++= Seq(
  "org.apache.spark" %% "spark-sql" % sparkVersion % "provided",
  "org.apache.spark" %% "spark-core" % sparkVersion % "provided",

  "org.apache.iceberg" %% "iceberg-spark-sql-catalyst" % icebergVersion,
  "org.apache.iceberg" %% "iceberg-spark" % icebergVersion,
  "org.apache.iceberg" % "iceberg-core" % icebergVersion,
  "org.apache.iceberg" % "iceberg-aws" % icebergVersion,

  "org.apache.hadoop" % "hadoop-aws" % "3.3.6",
  "software.amazon.awssdk" % "s3" % "2.24.0",
  "software.amazon.awssdk" % "sts" % "2.24.0",

  "com.fasterxml.jackson.core" % "jackson-databind" % "2.16.1",
  "com.fasterxml.jackson.module" %% "jackson-module-scala" % "2.16.1",

  "org.slf4j" % "slf4j-api" % "1.7.36",
  "org.slf4j" % "slf4j-log4j12" % "1.7.36",
  "log4j" % "log4j" % "1.2.17",

  "org.scalatest" %% "scalatest" % "3.2.17" % "test"
)

assembly / assemblyMergeStrategy := {
  case PathList("META-INF", xs @ _*) => MergeStrategy.discard
  case x => MergeStrategy.first
}

assembly / mainClass := Some("io.acraas.spark.HouseholdAggregationJob")

publishMavenStyle := true
