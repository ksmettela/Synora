package io.synora.sample

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import io.synora.sdk.SynoraSdk

class MainActivity : AppCompatActivity() {

    private lateinit var sdk: SynoraSdk
    private lateinit var statusText: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        statusText = findViewById(R.id.status_text)
        val consentBtn = findViewById<Button>(R.id.consent_btn)
        val startBtn = findViewById<Button>(R.id.start_btn)
        val stopBtn = findViewById<Button>(R.id.stop_btn)

        sdk = SynoraSdk(
            context = this,
            config = SynoraSdk.Config(
                serverUrl = "https://ingest.example.com",
                apiKey = "sample_mfr_demo_key",
            ),
        )

        updateStatus()

        consentBtn.setOnClickListener {
            sdk.setConsent(!sdk.isOptedIn())
            updateStatus()
        }
        startBtn.setOnClickListener {
            ensureAudioPermission {
                sdk.start()
                updateStatus()
            }
        }
        stopBtn.setOnClickListener {
            sdk.stop()
            updateStatus()
        }
    }

    private fun ensureAudioPermission(onGranted: () -> Unit) {
        if (ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.RECORD_AUDIO,
            ) == PackageManager.PERMISSION_GRANTED
        ) {
            onGranted()
        } else {
            pendingOnGranted = onGranted
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.RECORD_AUDIO),
                REQ_AUDIO,
            )
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray,
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQ_AUDIO &&
            grantResults.isNotEmpty() &&
            grantResults[0] == PackageManager.PERMISSION_GRANTED
        ) {
            pendingOnGranted?.invoke()
        }
        pendingOnGranted = null
    }

    private fun updateStatus() {
        val lines = listOf(
            "SDK ${SynoraSdk.VERSION}",
            "Device: ${sdk.deviceId().take(16)}…",
            "Consent: ${if (sdk.isOptedIn()) "GRANTED" else "OPTED OUT"}",
        )
        statusText.text = lines.joinToString("\n")
        statusText.visibility = View.VISIBLE
    }

    private var pendingOnGranted: (() -> Unit)? = null

    companion object {
        private const val REQ_AUDIO = 4711
    }
}
