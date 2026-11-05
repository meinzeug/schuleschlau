package de.dorfspy.schulpilot.qa

import android.app.Activity
import android.app.Instrumentation
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import de.dorfspy.schulpilot.AppUpdater
import java.io.File
import java.security.MessageDigest

/** Synthetic APKs on the explicitly isolated .updateprobe test package only. */
class UpdateProbeRegression(private val instrumentation: Instrumentation) {
    private class CaptureActivity(context: Context) : Activity() {
        var launches = 0
        var lastIntent: Intent? = null
        init { attachBaseContext(context) }
        override fun startActivity(intent: Intent?) { launches++; lastIntent = intent }
    }

    fun run() {
        val result = Bundle()
        try {
            val context = instrumentation.targetContext
            check(context.packageName.endsWith(".updateprobe")) { "not_isolated_package" }
            check(context.packageManager.canRequestPackageInstalls()) { "installer_permission_not_granted" }
            lateinit var activity: CaptureActivity
            instrumentation.runOnMainSync { activity = CaptureActivity(context) }
            val updater = AppUpdater(activity)
            val flags = if (Build.VERSION.SDK_INT >= 28) PackageManager.GET_SIGNING_CERTIFICATES else PackageManager.GET_SIGNATURES
            @Suppress("DEPRECATION")
            val installed = context.packageManager.getPackageInfo(context.packageName, flags)
            val current = if (Build.VERSION.SDK_INT >= 28) installed.longVersionCode else @Suppress("DEPRECATION") installed.versionCode.toLong()
            val incoming = File(context.filesDir, "update-probe")
            val cache = File(context.cacheDir, "updates").apply { mkdirs() }
            val verify = AppUpdater::class.java.getDeclaredMethod("verify", File::class.java, AppUpdater.Release::class.java, installed.javaClass).apply { isAccessible = true }
            val install = AppUpdater::class.java.getDeclaredMethod("install", File::class.java, AppUpdater.Release::class.java).apply { isAccessible = true }
            fun hash(file: File): String = MessageDigest.getInstance("SHA-256").digest(file.readBytes()).joinToString("") { "%02x".format(it) }
            fun copy(name: String): File = File(cache, name).also { File(incoming, name).copyTo(it, overwrite = true) }
            val good = copy("good.apk")
            val wrongPackage = copy("wrong-package.apk")
            val wrongSigner = copy("wrong-signer.apk")
            val wrongVersion = copy("wrong-version.apk")
            val oldVersion = copy("old-version.apk")
            val unsupportedSdk = copy("unsupported-sdk.apk")
            val goodRelease = AppUpdater.Release(current + 1, "synthetic", good.length(), hash(good), "https://example.invalid/")
            fun verified(file: File, release: AppUpdater.Release): Boolean = verify.invoke(updater, file, release, installed) as Boolean
            check(verified(good, goodRelease)) { "valid_rejected" }
            val bad = listOf(
                good to goodRelease.copy(size = good.length() + 1),
                good to goodRelease.copy(sha = "0".repeat(64)),
                wrongPackage to goodRelease.copy(size = wrongPackage.length(), sha = hash(wrongPackage)),
                wrongSigner to goodRelease.copy(size = wrongSigner.length(), sha = hash(wrongSigner)),
                wrongVersion to goodRelease.copy(size = wrongVersion.length(), sha = hash(wrongVersion)),
                oldVersion to goodRelease.copy(code = current, size = oldVersion.length(), sha = hash(oldVersion)),
                unsupportedSdk to goodRelease.copy(size = unsupportedSdk.length(), sha = hash(unsupportedSdk)),
            )
            for ((file, release) in bad) {
                check(!verified(file, release)) { "invalid_accepted" }
                instrumentation.runOnMainSync { install.invoke(updater, file, release) }
                check(activity.launches == 0) { "invalid_opened_installer" }
            }
            instrumentation.runOnMainSync { install.invoke(updater, good, goodRelease) }
            check(activity.launches == 1) { "valid_not_opened" }
            check(activity.lastIntent?.action == Intent.ACTION_VIEW &&
                activity.lastIntent?.data?.scheme == "content" &&
                activity.lastIntent?.data?.authority == context.packageName + ".updates" &&
                activity.lastIntent?.flags?.and(Intent.FLAG_GRANT_READ_URI_PERMISSION) != 0) { "invalid_install_intent" }
            updater.close()
            cache.deleteRecursively()
            result.putString("stream", "OK: valid, size, hash, package, signer, version, downgrade, min_sdk, installer_gate\n")
            instrumentation.finish(Activity.RESULT_OK, result)
        } catch (error: Throwable) {
            val cause = error.cause
            val frames = error.stackTrace.take(5).joinToString(";") { it.className + "." + it.methodName + ":" + it.lineNumber }
            android.util.Log.e("UpdateProbe", error.javaClass.simpleName + "/" + (cause?.javaClass?.simpleName ?: "none") + " " + frames)
            result.putString("stream", "FAILED: " + (error.message?.takeIf { it.matches(Regex("[a-z_]+")) } ?: error.javaClass.simpleName) + "\n")
            instrumentation.finish(Activity.RESULT_CANCELED, result)
        }
    }
}
