package io.synora.sdk.internal

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import android.util.Log

/**
 * Local store for fingerprints awaiting upload. Survives process death, power
 * cycles, and offline periods. Bounded at [capacity] — oldest rows drop
 * first so the cache cannot grow unbounded on devices that stay offline
 * indefinitely.
 */
internal class FingerprintCache(
    context: Context,
    private val capacity: Int = 500,
) : SQLiteOpenHelper(context.applicationContext, DB_NAME, null, DB_VERSION) {

    data class Row(val id: Long, val fingerprintHex: String, val capturedAtMs: Long)

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL(
            """
            CREATE TABLE fingerprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fingerprint_hex TEXT NOT NULL,
                captured_at_ms INTEGER NOT NULL
            )
            """.trimIndent(),
        )
        db.execSQL("CREATE INDEX idx_fp_captured ON fingerprints(captured_at_ms)")
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        db.execSQL("DROP TABLE IF EXISTS fingerprints")
        onCreate(db)
    }

    fun insert(fingerprintHex: String, capturedAtMs: Long) {
        writableDatabase.use { db ->
            db.beginTransaction()
            try {
                db.execSQL(
                    "INSERT INTO fingerprints (fingerprint_hex, captured_at_ms) VALUES (?, ?)",
                    arrayOf(fingerprintHex, capturedAtMs),
                )
                // Trim to capacity (oldest first).
                db.execSQL(
                    """
                    DELETE FROM fingerprints
                    WHERE id NOT IN (
                        SELECT id FROM fingerprints
                        ORDER BY captured_at_ms DESC
                        LIMIT ?
                    )
                    """.trimIndent(),
                    arrayOf(capacity),
                )
                db.setTransactionSuccessful()
            } finally {
                db.endTransaction()
            }
        }
    }

    fun drainBatch(max: Int): List<Row> {
        val rows = mutableListOf<Row>()
        readableDatabase.use { db ->
            db.rawQuery(
                "SELECT id, fingerprint_hex, captured_at_ms FROM fingerprints ORDER BY captured_at_ms ASC LIMIT ?",
                arrayOf(max.toString()),
            ).use { c ->
                while (c.moveToNext()) {
                    rows.add(
                        Row(
                            id = c.getLong(0),
                            fingerprintHex = c.getString(1),
                            capturedAtMs = c.getLong(2),
                        ),
                    )
                }
            }
        }
        return rows
    }

    fun remove(ids: Collection<Long>) {
        if (ids.isEmpty()) return
        val placeholders = ids.joinToString(",") { "?" }
        writableDatabase.use { db ->
            db.execSQL(
                "DELETE FROM fingerprints WHERE id IN ($placeholders)",
                ids.map { it as Any }.toTypedArray(),
            )
        }
    }

    fun purgeAll() {
        writableDatabase.use { db ->
            db.execSQL("DELETE FROM fingerprints")
        }
        Log.i(TAG, "cache purged")
    }

    companion object {
        private const val DB_NAME = "synora_sdk.db"
        private const val DB_VERSION = 1
        private const val TAG = "SynoraCache"
    }
}
