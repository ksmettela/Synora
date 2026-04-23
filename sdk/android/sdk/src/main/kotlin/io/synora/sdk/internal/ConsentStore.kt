package io.synora.sdk.internal

import android.content.Context
import android.content.SharedPreferences

/**
 * Persistent consent state. Defaults to opted-out until the manufacturer app
 * explicitly opts the user in through an in-TV consent flow — Synora never
 * assumes consent.
 */
internal class ConsentStore(context: Context) {
    private val prefs: SharedPreferences =
        context.applicationContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    var optedIn: Boolean
        get() = prefs.getBoolean(KEY_OPTED_IN, false)
        set(value) {
            prefs.edit().putBoolean(KEY_OPTED_IN, value).apply()
        }

    companion object {
        private const val PREFS_NAME = "synora_sdk_consent"
        private const val KEY_OPTED_IN = "opted_in"
    }
}
