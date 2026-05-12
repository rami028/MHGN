package com.example.ckdvmf

import android.Manifest
import android.app.AppOpsManager
import android.app.usage.UsageEvents
import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.CallLog
import android.provider.Settings
import android.provider.Telephony
import androidx.core.content.ContextCompat
import org.json.JSONObject
import java.io.File
import java.time.Instant
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.ZoneId
import kotlin.math.pow

class FeatureCollector(private val context: Context) {
    private val zoneId: ZoneId = ZoneId.systemDefault()

    fun collectToday(): CollectionResult {
        val now = System.currentTimeMillis()
        val start = LocalDate.now(zoneId)
            .atStartOfDay(zoneId)
            .toInstant()
            .toEpochMilli()

        val usage = collectUsageFeatures(start, now)
        val call = collectCallFeatures(start, now)
        val sms = collectSmsFeatures(start, now)

        val json = JSONObject()
            .put("generated_at_epoch_ms", now)
            .put("collection_window_start_epoch_ms", start)
            .put("collection_window_end_epoch_ms", now)
            .put("total_screentime_hours", usage.totalScreenTimeHours)
            .put("time_spent_socialmedia_hours", usage.socialMediaHours)
            .put("time_spent_game_hours", usage.gameHours)
            .put("last_phone_log_time_minutes", usage.lastUseMinutes)
            .put("first_phone_log_time_minutes", usage.firstUseMinutes)
            .put("night_screentime_hours", usage.nightScreenTimeHours)
            .put("number_calls", call.numberCalls)
            .put("total_call_duration_minutes", call.totalCallDurationMinutes)
            .put("variance_call_duration", call.varianceCallDuration)
            .put("number_messages", sms.numberMessages)
            .put("mobility_time_hours", 0.0)
            .put("resting_time_hours", 8.0)
            .put("avg_sleep_time_hours", 7.0)
            .put("var_sleep_time", 0.0)
            .put("avg_heartrate_bpm", 75.0)
            .put("var_heartrate", 0.0)
            .put("number_steps", 0.0)
            .put("distance_traveled_km", 0.0)
            .put("usage_stats_permission", hasUsageStatsPermission(context))
            .put("call_log_permission", hasPermission(Manifest.permission.READ_CALL_LOG))
            .put("sms_permission", hasPermission(Manifest.permission.READ_SMS))

        val dir = context.getExternalFilesDir(null) ?: context.filesDir
        val file = File(dir, "user_features.json")
        file.writeText(json.toString(2), Charsets.UTF_8)

        return CollectionResult(
            jsonText = json.toString(2),
            savedPath = file.absolutePath
        )
    }

    fun openUsageAccessSettings() {
        val intent = Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS)
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(intent)
    }

    fun hasUsageStatsPermission(context: Context = this.context): Boolean {
        val appOps = context.getSystemService(Context.APP_OPS_SERVICE) as AppOpsManager
        val mode = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            appOps.unsafeCheckOpNoThrow(
                AppOpsManager.OPSTR_GET_USAGE_STATS,
                android.os.Process.myUid(),
                context.packageName
            )
        } else {
            @Suppress("DEPRECATION")
            appOps.checkOpNoThrow(
                AppOpsManager.OPSTR_GET_USAGE_STATS,
                android.os.Process.myUid(),
                context.packageName
            )
        }
        return mode == AppOpsManager.MODE_ALLOWED
    }

    private fun collectUsageFeatures(startMs: Long, endMs: Long): UsageFeatureSet {
        if (!hasUsageStatsPermission()) {
            return UsageFeatureSet()
        }

        val usageStatsManager = context.getSystemService(Context.USAGE_STATS_SERVICE)
            as UsageStatsManager
        val events = usageStatsManager.queryEvents(startMs, endMs)
        val event = UsageEvents.Event()
        val activeStartByPackage = mutableMapOf<String, Long>()

        var totalMs = 0L
        var socialMs = 0L
        var gameMs = 0L
        var nightMs = 0L
        var firstUseMinutes: Int? = null
        var lastUseMinutes = 0

        while (events.hasNextEvent()) {
            events.getNextEvent(event)
            val packageName = event.packageName ?: continue

            if (isForegroundStartEvent(event.eventType)) {
                activeStartByPackage[packageName] = event.timeStamp
                val minutes = minutesSinceMidnight(event.timeStamp)
                firstUseMinutes = minOf(firstUseMinutes ?: minutes, minutes)
                lastUseMinutes = maxOf(lastUseMinutes, minutes)
            }

            if (isForegroundEndEvent(event.eventType)) {
                val sessionStart = activeStartByPackage.remove(packageName) ?: continue
                val sessionEnd = event.timeStamp
                if (sessionEnd <= sessionStart) continue

                val duration = sessionEnd - sessionStart
                totalMs += duration
                nightMs += nightOverlapMs(sessionStart, sessionEnd)

                if (isSocialPackage(packageName)) {
                    socialMs += duration
                }
                if (isGamePackage(packageName)) {
                    gameMs += duration
                }

                val minutes = minutesSinceMidnight(sessionEnd)
                lastUseMinutes = maxOf(lastUseMinutes, minutes)
            }
        }

        return UsageFeatureSet(
            totalScreenTimeHours = totalMs.toHours(),
            socialMediaHours = socialMs.toHours(),
            gameHours = gameMs.toHours(),
            nightScreenTimeHours = nightMs.toHours(),
            firstUseMinutes = firstUseMinutes ?: 0,
            lastUseMinutes = lastUseMinutes
        )
    }

    private fun collectCallFeatures(startMs: Long, endMs: Long): CallFeatureSet {
        if (!hasPermission(Manifest.permission.READ_CALL_LOG)) {
            return CallFeatureSet()
        }

        val durations = mutableListOf<Double>()
        val projection = arrayOf(CallLog.Calls.DATE, CallLog.Calls.DURATION)
        val selection = "${CallLog.Calls.DATE} >= ? AND ${CallLog.Calls.DATE} <= ?"
        val selectionArgs = arrayOf(startMs.toString(), endMs.toString())

        context.contentResolver.query(
            CallLog.Calls.CONTENT_URI,
            projection,
            selection,
            selectionArgs,
            null
        )?.use { cursor ->
            val durationIndex = cursor.getColumnIndexOrThrow(CallLog.Calls.DURATION)
            while (cursor.moveToNext()) {
                durations.add(cursor.getLong(durationIndex).toDouble() / 60.0)
            }
        }

        val total = durations.sum()
        val mean = if (durations.isEmpty()) 0.0 else total / durations.size
        val variance = if (durations.isEmpty()) {
            0.0
        } else {
            durations.map { (it - mean).pow(2.0) }.average()
        }

        return CallFeatureSet(
            numberCalls = durations.size,
            totalCallDurationMinutes = total,
            varianceCallDuration = variance
        )
    }

    private fun collectSmsFeatures(startMs: Long, endMs: Long): SmsFeatureSet {
        if (!hasPermission(Manifest.permission.READ_SMS)) {
            return SmsFeatureSet()
        }

        var count = 0
        val projection = arrayOf(Telephony.Sms.DATE)
        val selection = "${Telephony.Sms.DATE} >= ? AND ${Telephony.Sms.DATE} <= ?"
        val selectionArgs = arrayOf(startMs.toString(), endMs.toString())

        context.contentResolver.query(
            Telephony.Sms.CONTENT_URI,
            projection,
            selection,
            selectionArgs,
            null
        )?.use { cursor ->
            count = cursor.count
        }

        return SmsFeatureSet(numberMessages = count)
    }

    private fun hasPermission(permission: String): Boolean {
        return ContextCompat.checkSelfPermission(context, permission) ==
            PackageManager.PERMISSION_GRANTED
    }

    private fun isForegroundStartEvent(eventType: Int): Boolean {
        return eventType == UsageEvents.Event.MOVE_TO_FOREGROUND ||
            (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q &&
                eventType == UsageEvents.Event.ACTIVITY_RESUMED)
    }

    private fun isForegroundEndEvent(eventType: Int): Boolean {
        return eventType == UsageEvents.Event.MOVE_TO_BACKGROUND ||
            (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q &&
                eventType == UsageEvents.Event.ACTIVITY_PAUSED)
    }

    private fun isSocialPackage(packageName: String): Boolean {
        val socialPackages = setOf(
            "com.kakao.talk",
            "com.instagram.android",
            "com.facebook.katana",
            "com.facebook.orca",
            "com.twitter.android",
            "com.zhiliaoapp.musically",
            "com.snapchat.android",
            "org.telegram.messenger",
            "com.discord",
            "jp.naver.line.android",
            "com.whatsapp"
        )
        return packageName in socialPackages
    }

    private fun isGamePackage(packageName: String): Boolean {
        return try {
            val appInfo = context.packageManager.getApplicationInfo(packageName, 0)
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.O &&
                appInfo.category == ApplicationInfo.CATEGORY_GAME
        } catch (_: Exception) {
            false
        }
    }

    private fun minutesSinceMidnight(timestampMs: Long): Int {
        val dateTime = LocalDateTime.ofInstant(Instant.ofEpochMilli(timestampMs), zoneId)
        return dateTime.hour * 60 + dateTime.minute
    }

    private fun nightOverlapMs(sessionStart: Long, sessionEnd: Long): Long {
        val dayStart = LocalDate.now(zoneId).atStartOfDay(zoneId).toInstant().toEpochMilli()
        val morningEnd = dayStart + 6 * 60 * 60 * 1000L
        val nightStart = dayStart + 22 * 60 * 60 * 1000L
        val dayEnd = dayStart + 24 * 60 * 60 * 1000L

        return overlap(sessionStart, sessionEnd, dayStart, morningEnd) +
            overlap(sessionStart, sessionEnd, nightStart, dayEnd)
    }

    private fun overlap(startA: Long, endA: Long, startB: Long, endB: Long): Long {
        val start = maxOf(startA, startB)
        val end = minOf(endA, endB)
        return maxOf(0L, end - start)
    }

    private fun Long.toHours(): Double = this / 1000.0 / 60.0 / 60.0
}

private data class UsageFeatureSet(
    val totalScreenTimeHours: Double = 0.0,
    val socialMediaHours: Double = 0.0,
    val gameHours: Double = 0.0,
    val nightScreenTimeHours: Double = 0.0,
    val firstUseMinutes: Int = 0,
    val lastUseMinutes: Int = 0
)

private data class CallFeatureSet(
    val numberCalls: Int = 0,
    val totalCallDurationMinutes: Double = 0.0,
    val varianceCallDuration: Double = 0.0
)

private data class SmsFeatureSet(
    val numberMessages: Int = 0
)
