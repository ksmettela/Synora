"""SQL segment builder for Trino queries."""
import json
from typing import Optional
from models.segment import SegmentDefinition, SegmentRule


class SegmentSQLBuilder:
    """Builds Trino SQL from segment definitions."""

    def __init__(self, catalog: str = "iceberg", schema: str = "acraas"):
        self.catalog = catalog
        self.schema = schema
        self.table = f"{catalog}.{schema}.viewership"

    def build_sql(self, segment: SegmentDefinition, segment_id: str) -> str:
        """Build Trino SQL for segment definition."""
        rule_conditions = []

        for rule in segment.rules:
            condition = self._build_rule_sql(rule)
            if condition:
                rule_conditions.append(condition)

        # Combine conditions with AND/OR logic
        if segment.logic == "AND":
            where_clause = " AND ".join([f"({c})" for c in rule_conditions])
        else:
            where_clause = " OR ".join([f"({c})" for c in rule_conditions])

        # Apply lookback window
        lookback_sql = f"""
        SELECT
            DISTINCT household_id,
            device_id,
            CURRENT_TIMESTAMP as segment_timestamp
        FROM {self.table}
        WHERE {where_clause}
            AND viewing_date >= CURRENT_DATE - INTERVAL '{segment.lookback_days}' day
        """

        return lookback_sql

    def _build_rule_sql(self, rule: SegmentRule) -> Optional[str]:
        """Build SQL condition for single rule."""
        rule_type = rule.type

        if rule_type == "watched_genre":
            return self._genre_condition(rule)
        elif rule_type == "watched_network":
            return self._network_condition(rule)
        elif rule_type == "household_income":
            return self._income_condition(rule)
        elif rule_type == "dma":
            return self._dma_condition(rule)
        elif rule_type == "daypart":
            return self._daypart_condition(rule)

        return None

    def _genre_condition(self, rule: SegmentRule) -> str:
        """Build genre condition."""
        if isinstance(rule.value, list):
            genres = "', '".join(rule.value)
            return f"genre IN ('{genres}')"
        return f"genre = '{rule.value}'"

    def _network_condition(self, rule: SegmentRule) -> str:
        """Build network condition."""
        if isinstance(rule.value, list):
            networks = "', '".join(rule.value)
            return f"network IN ('{networks}')"
        return f"network = '{rule.value}'"

    def _income_condition(self, rule: SegmentRule) -> str:
        """Build household income condition."""
        if rule.operator == ">=":
            return f"household_income >= {rule.value}"
        elif rule.operator == "<=":
            return f"household_income <= {rule.value}"
        else:
            return f"household_income = {rule.value}"

    def _dma_condition(self, rule: SegmentRule) -> str:
        """Build DMA condition."""
        if isinstance(rule.value, list):
            dmas = ", ".join(map(str, rule.value))
            return f"dma_code IN ({dmas})"
        return f"dma_code = {rule.value}"

    def _daypart_condition(self, rule: SegmentRule) -> str:
        """Build daypart condition."""
        if isinstance(rule.value, list):
            dayparts = "', '".join(rule.value)
            return f"daypart IN ('{dayparts}')"
        return f"daypart = '{rule.value}'"


class TrinoQueryExecutor:
    """Executes Trino SQL queries."""

    def __init__(self, host: str, port: int, catalog: str, schema: str, user: str):
        self.host = host
        self.port = port
        self.catalog = catalog
        self.schema = schema
        self.user = user

    async def execute_segment_query(self, sql: str) -> dict:
        """Execute segment query and return device/household counts."""
        try:
            from trino.dbapi import connect

            conn = connect(
                host=self.host,
                port=self.port,
                user=self.user,
            )
            cursor = conn.cursor()

            # Execute COUNT queries
            device_count_sql = f"""
            WITH segment_data AS (
                {sql}
            )
            SELECT COUNT(DISTINCT device_id) as device_count,
                   COUNT(DISTINCT household_id) as household_count
            FROM segment_data
            """

            cursor.execute(device_count_sql)
            result = cursor.fetchone()

            return {
                "device_count": result[0] if result else 0,
                "household_count": result[1] if result else 0,
            }
        except Exception as e:
            raise Exception(f"Trino query execution failed: {str(e)}")
