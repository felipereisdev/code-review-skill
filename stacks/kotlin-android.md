# Kotlin / Android — Code Review Checklist

> Check sibling files and modules for existing patterns before flagging a convention (see Consistency Check step). Report an item only with a concrete trigger → effect in the changed code. A problem that the Kotlin compiler, Android Lint, detekt or ktlint, as the repository configures them, already reports is not a finding. The `## Kotlin` sections apply to the `.kt` and `.kts` files of a module whose build applies a Kotlin plugin or an Android plugin. The `## Android` sections apply only to a module whose own build applies `com.android.application` or `com.android.library`, including its Java sources and its `AndroidManifest.xml`; a Kotlin build without one of them is a JVM, server or multiplatform module, never an Android app. Read the Kotlin version and plugins from the module's build file and the version catalog, and `minSdk`, `targetSdk` and `compileSdk` from the Android block; an item that names an API level or a `targetSdk` applies only from that level.

## Kotlin: Null Safety and Java Interop

- **Values that can be null treated as non-null**: `!!` on a value that a map lookup, a Java API, an intent extra or a deserializer can return as `null` throws a `NullPointerException`. A Java method without nullability annotations returns a platform type (`String!`); assigning it to a non-null Kotlin type makes Kotlin insert a check that throws at that point when the value is `null`. Report it when the Java documentation, or the code, says the method can return `null`. **Not a finding:** a value checked just before, and Java APIs annotated `@NonNull`, which Kotlin reads as non-null types.

## Kotlin: Coroutines

- **Cancellation swallowed**: `catch (e: Exception)` or `runCatching` around a suspending call also catches `CancellationException`, so a cancelled coroutine keeps running the code after the `catch` (for example, it writes a result for a screen that is gone, or retries forever). Rethrow `CancellationException`, or catch only the exceptions the call documents. **Not a finding:** a `catch` that rethrows, and code that only logs and then ends.
- **Scopes that outlive their owner**: `GlobalScope.launch`, or a `CoroutineScope(...)` that nothing cancels, runs after the screen, request or object that started it is gone, keeps references to it, and is never stopped on logout or shutdown. Use the owner's scope (`viewModelScope`, `lifecycleScope`, or a scope that the owner cancels).
- **Blocking calls in coroutines**: `Thread.sleep`, blocking I/O, `runBlocking` or a long CPU loop on `Dispatchers.Main` freezes the UI and, on Android, leads to an "Application Not Responding" dialog; on `Dispatchers.Default` it takes one of a few shared threads. Use `withContext(Dispatchers.IO)` for blocking I/O and `delay` instead of `Thread.sleep`. `runBlocking` on the main thread that waits for work dispatched to the main thread deadlocks.

**Bad** — if the ViewModel is cleared while `fetchStatus` runs, the `catch` also swallows the cancellation and writes its message to `_error` for a ViewModel that is gone; the `delay` after the `try` then throws, so the loop ends:

```kotlin
fun startPolling() = viewModelScope.launch {
    while (true) {
        try {
            _status.value = api.fetchStatus()
        } catch (e: Exception) {
            _error.value = e.message
        }
        delay(5_000)
    }
}
```

**Good** — cancellation is rethrown, so the loop ends when the scope is cancelled:

```kotlin
fun startPolling() = viewModelScope.launch {
    while (true) {
        try {
            _status.value = api.fetchStatus()
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            _error.value = e.message
        }
        delay(5_000)
    }
}
```

## Android: Components and Intents

- **Exported components that trust their input**: an activity, service, receiver or provider with `android:exported="true"` can be started or called by any app on the device. Report one that the change exports, or that acts on intent extras or URI parameters without checking them: one that loads a URL from an extra into a `WebView`, returns files or data, or performs an account action. Since Android 12 (`targetSdk` 31), a component with an intent filter must declare `android:exported` explicitly, or the build fails. **Not a finding:** exporting the launcher activity itself, which the launcher needs in order to start it, when that activity does not act on unchecked extras or data (a launcher intent filter alone is not an exemption), and components protected by a permission with `android:protectionLevel="signature"`.
- **Mutable `PendingIntent` with an implicit intent**: a `PendingIntent` is mutable when it is created with `FLAG_MUTABLE`, or without `FLAG_IMMUTABLE` in an app whose `targetSdk` is 30 or lower, on any device. For `targetSdk` 31 or higher, it is also mutable when created without `FLAG_IMMUTABLE` on a device running Android 11 (API 30) or lower. A mutable `PendingIntent` around an intent without an explicit component lets the app that receives it fill in the target and the extras, and act with this app's identity. Apps targeting Android 12 (API 31) or higher must set `FLAG_IMMUTABLE` or `FLAG_MUTABLE`. Apps targeting Android 14 (API 34) or higher get an `IllegalArgumentException` when they create a mutable `PendingIntent` with an implicit intent on an Android 14 or later device, unless they also set `FLAG_ALLOW_UNSAFE_IMPLICIT_INTENT`; with that flag, or on an earlier device, the hijack described above is possible. Use `FLAG_IMMUTABLE` and an explicit intent unless the receiver must change it, such as inline reply. **Not a finding:** a mutable `PendingIntent` whose intent names its component, when the app validates the extras it reads from the receiver's fill-in.
- **WebView bridges**: `addJavascriptInterface` exposes the annotated methods of an object to every page that the `WebView` loads, including pages reached through redirects or links. Report it in a `WebView` that can load content that the app does not control. `WebSettings.setAllowFileAccess` defaults to `true` for `targetSdk` 29 and lower and to `false` from `targetSdk` 30. Report a `WebView` with file access on, explicitly or through that default, that loads a URL from an external source (an intent extra, a deep link or a redirect): such a URL can select an app-private `file://` resource, and the `WebView` then loads that file with the app's access. Enabling file access alone does not let an `https` or app-asset page read app files. Script on a `file://` page reads other `file://` files only with `setAllowFileAccessFromFileURLs` or `setAllowUniversalAccessFromFileURLs` on (both default to `false` from `targetSdk` 16), so report those only where attacker-controlled script or content can reach that page. **Not a finding:** file access on in a `WebView` that loads only `https` pages or app-owned assets.
- **Network or disk work on the main thread**: a network call on the main thread throws `NetworkOnMainThreadException`, a crash rather than a slowdown; a Room query on the main thread throws `IllegalStateException` unless `allowMainThreadQueries()` is set.
- **Contexts kept beyond their lifetime**: an `Activity`, `View` or `Fragment` stored in a companion object, a singleton or a `ViewModel` stays in memory after the screen is destroyed (for example on rotation), with its whole view tree. Keep the application context, or a lifecycle-aware reference.

**Bad** — on `targetSdk` 33 or lower, any app that gets this `PendingIntent` can choose where it goes and what it carries. On `targetSdk` 34 and higher, creating it fails on Android 14 and later, so the hijack needs `FLAG_ALLOW_UNSAFE_IMPLICIT_INTENT` added or a device below Android 14:

```kotlin
val intent = Intent("com.acme.ACTION_OPEN_ORDER")
val pending = PendingIntent.getActivity(context, 0, intent, PendingIntent.FLAG_MUTABLE)
```

**Good** — the intent names its component, and the receiver cannot change it:

```kotlin
val intent = Intent(context, OrderActivity::class.java)
val pending = PendingIntent.getActivity(context, 0, intent, PendingIntent.FLAG_IMMUTABLE)
```

## Android: Data and Network

- **Secrets in the APK**: values in `BuildConfig` fields, `strings.xml`, assets or code ship inside the APK and can be extracted from it. Report a server secret, such as a signing key or an API key that grants write or billing access. **Not a finding:** keys that the provider restricts to the app's package and signing certificate, such as a restricted Maps key.
- **Cleartext traffic**: `android:usesCleartextTraffic="true"` or a network security config with `cleartextTrafficPermitted="true"` allows HTTP. Cleartext is blocked by default from `targetSdk` 28. Report a change that allows it for a host that receives credentials or personal data. **Not a finding:** a debug-only `<debug-overrides>` block, and local hosts in development builds.

## Conventions, not defects

- MVVM versus MVI, Jetpack Compose versus Views, the dependency injection framework, Flow versus LiveData, and the module layout follow the repository's conventions.
- `lateinit`, scope functions (`let`, `apply`, `also`) and extension functions are style choices; they are findings only with a concrete failure, such as reading a `lateinit` property before it is set.

## Sources

- Null safety and platform types: https://kotlinlang.org/docs/null-safety.html, https://kotlinlang.org/docs/java-interop.html#null-safety-and-platform-types
- Cancellation and exceptions: https://kotlinlang.org/docs/cancellation-and-timeouts.html, https://kotlinlang.org/docs/exception-handling.html; Android coroutine main-safety (`suspend` alone does not move work off the main thread, so use `withContext`): https://developer.android.com/kotlin/coroutines/coroutines-best-practices, https://developer.android.com/kotlin/coroutines/coroutines-adv
- Room and Retrofit `suspend` main-safety: https://developer.android.com/training/data-storage/room/async-queries (one-shot `suspend` queries are asynchronous); https://raw.githubusercontent.com/square/retrofit/parent-2.6.0/retrofit/src/main/java/retrofit2/KotlinExtensions.kt (`await()` enqueues the call inside `suspendCancellableCoroutine`; Retrofit 2.6.0 tag)
- Lifecycle-aware scopes and `repeatOnLifecycle`: https://developer.android.com/topic/libraries/architecture/views/coroutines-views
- `android:exported`: https://developer.android.com/guide/topics/manifest/activity-element#exported, https://developer.android.com/about/versions/12/behavior-changes-12#exported; providers: https://developer.android.com/guide/topics/manifest/provider-element#exported
- `PendingIntent` mutability (mutable by default for `targetSdk` 30 or lower on any device, and for `targetSdk` 31 or higher on devices up to Android 11; explicit mutability required for `targetSdk` 31 or higher from Android 12; implicit intents rejected from Android 14 for `targetSdk` 34): https://developer.android.com/reference/android/app/PendingIntent, https://developer.android.com/about/versions/12/behavior-changes-12#pending-intent-mutability, https://developer.android.com/privacy-and-security/risks/pending-intent
- WebView: https://developer.android.com/reference/android/webkit/WebView#addJavascriptInterface(java.lang.Object,%20java.lang.String), https://developer.android.com/reference/android/webkit/WebSettings#setAllowFileAccess(boolean), https://developer.android.com/reference/android/webkit/WebSettings#setAllowFileAccessFromFileURLs(boolean), https://developer.android.com/reference/android/webkit/WebSettings#setAllowUniversalAccessFromFileURLs(boolean); file-access risk: https://developer.android.com/privacy-and-security/risks/webview-unsafe-file-inclusion
- Network security configuration: https://developer.android.com/privacy-and-security/security-config; `NetworkOnMainThreadException`: https://developer.android.com/reference/android/os/NetworkOnMainThreadException; Room on the main thread: https://developer.android.com/training/data-storage/room/async-queries; `allowMainThreadQueries()` disables the check: https://developer.android.com/reference/androidx/room/RoomDatabase.Builder#allowMainThreadQueries(); the `IllegalStateException` check (`assertNotMainThread`) in the Room runtime 2.8.5 sources: https://dl.google.com/dl/android/maven2/androidx/room/room-runtime-android/2.8.5/room-runtime-android-2.8.5-sources.jar

## Precedents

- **Room and Retrofit suspend functions are main-safe**: Room DAO `suspend` functions and Retrofit `suspend` service functions (Retrofit 2.6.0 and later) run their work off the calling thread, so calling them from `Dispatchers.Main`, for example inside `viewModelScope.launch`, does not block it. Do not report such calls as I/O on the main thread. **Exception:** non-suspending Room DAO methods, Retrofit `Call.execute()`, OkHttp `execute()`, other blocking clients, and work around the call, such as parsing a large response or reading a file, on the main thread.
- **`viewModelScope` and `lifecycleScope` cancel their coroutines**: coroutines launched in `viewModelScope` are cancelled when the `ViewModel` is cleared, and those in `lifecycleScope` when the lifecycle is destroyed. Do not report them as leaked after their owner is gone. **Exception:** work started in `GlobalScope` or in a scope that nothing cancels, `NonCancellable` blocks, code that swallows `CancellationException`, blocking code that never checks for cancellation, and flows collected in `lifecycleScope.launch` without `repeatOnLifecycle`, which keep collecting while the app is in the background until the lifecycle is destroyed.
- **Kotlin types reject unchecked nulls**: the compiler rejects a dereference of a nullable Kotlin type without a check. Do not report a possible null dereference of a non-null Kotlin type. **Exception:** `!!`, platform types from Java, `lateinit` properties read before they are set, and objects created by reflection or by serialization libraries that bypass constructors, such as Gson, which can leave a non-null property `null`.
- **Components without an intent filter are not exported by default**: on Android, `android:exported` defaults to `false` for an activity, service or receiver that has no intent filter. Do not report such a component as reachable by other apps. **Exception:** `android:exported="true"`, a component with an `<intent-filter>` and no explicit `android:exported` in an app whose `targetSdk` is 30 or lower, where the default is `true`, content providers in apps whose `minSdk` or `targetSdk` is 16 or lower, where the default is `true`, and components reached through a `PendingIntent` that the app hands to another app.
