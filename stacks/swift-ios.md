# Swift / iOS — Code Review Checklist

> Check sibling files for existing patterns before flagging a convention (see Consistency Check step). Report an item only with a concrete trigger → effect in the changed code. A problem that the Swift compiler or SwiftLint, as the repository configures them, already reports is not a finding. The `## Swift` sections apply to every changed `.swift` file of a Swift package or Xcode project. The `## iOS` sections apply only with iOS evidence: `SDKROOT = iphoneos` in the project's `project.pbxproj`, an `.iOS(` entry in the `platforms` of `Package.swift` (for the code that runs on iOS), or an `import UIKit` in the changed file. `Package.swift` alone never proves an iOS app, and server-side Swift, such as a Vapor service, gets only the `## Swift` sections. Read the Swift language mode from `swiftLanguageModes` or the `swift-tools-version` line of `Package.swift`, or `SWIFT_VERSION` in the Xcode project, and the deployment target from `platforms` or `IPHONEOS_DEPLOYMENT_TARGET`; an item that names a version applies only from that version.

## Swift: Optionals and Errors

- **Crashes on external data**: force unwrap (`!`), `try!`, `as!`, an array index or arithmetic that overflows traps and ends the app when the value comes from the network, a decoder, a file, user input or a URL. Swift traps on overflow in debug and release builds alike (except `-Ounchecked`). Use `guard let`, `try` with handling, `as?`, a bounds check, or the overflow-reporting methods. **Not a finding:** literals that cannot fail, such as `URL(string: "https://example.com")!`, and `@IBOutlet` properties that the storyboard sets.
- **Errors discarded with `try?`**: `try? data.write(to: url)` or `try? context.save()` turns a failed write into `nil`, which the code then ignores, so the user's data is lost without any message. **Not a finding:** a `try?` whose `nil` result the code handles.

## Swift: Concurrency and Memory

- **UI updates off the main thread**: UIKit and AppKit views must be used on the main thread. A `URLSession` completion handler, a `NotificationCenter` observer for a notification posted from another thread, or a `DispatchQueue.global()` block that updates a view or a view model that drives the UI can crash or corrupt the UI. Hop to the main actor (`await MainActor.run`, `@MainActor` types, `DispatchQueue.main.async`). In the Swift 6 language mode, the compiler rejects most of these calls for `@MainActor` types; in the Swift 5 mode with minimal checking, it does not.
- **Actor reentrancy**: an actor method that reads its state, then `await`s, then acts on the value it read can act on stale state, because other calls to the actor can run during the `await`. Check the state again after the `await`, or keep the check and the change in one synchronous section.
- **Checks turned off**: `@unchecked Sendable`, `nonisolated(unsafe)` and `@preconcurrency` imports disable the compiler's data-race checks for that type, value or module. Report one that the change adds to a type with mutable state that no lock or queue protects.
- **Retain cycles in stored closures**: a closure that `self` keeps (a property, a Combine subscription stored in `self.cancellables`, a `Timer` that the run loop keeps, or a `NotificationCenter` block observer that `self` stores) and that captures `self` strongly keeps both alive forever. Capture `[weak self]`, or invalidate and cancel the closure in a teardown that runs. **Not a finding:** non-escaping closures, `UIView.animate` and one-shot `DispatchQueue.main.async` blocks, which are released after they run.

**Bad** — another call can reserve the last seat during the `await`, so both reservations succeed:

```swift
actor SeatMap {
    private var free: Set<String> = []

    func reserve(_ seat: String, for user: User) async throws {
        guard free.contains(seat) else { throw SeatError.taken }
        try await payments.authorize(user)
        free.remove(seat)
    }
}
```

**Good** — the seat is taken before the `await` and given back if the payment fails:

```swift
actor SeatMap {
    private var free: Set<String> = []

    func reserve(_ seat: String, for user: User) async throws {
        guard free.remove(seat) != nil else { throw SeatError.taken }
        do {
            try await payments.authorize(user)
        } catch {
            free.insert(seat)
            throw error
        }
    }
}
```

## iOS: Storage, Network and Entry Points

- **Credentials outside the Keychain**: a session token, password or refresh token stored in `UserDefaults`, a plist or a plain file lives unencrypted in the app container (apart from data protection while the device is locked), is included in backups and can be read by anything that reads that container. Store it in the Keychain with an accessibility class that matches its use. **Not a finding:** non-secret settings and identifiers.
- **App Transport Security exceptions**: `NSAllowsArbitraryLoads` or a per-domain `NSExceptionAllowsInsecureHTTPLoads` in `Info.plist` allows cleartext HTTP for `URLSession` and web views. Report a change that adds one for a host that receives credentials or personal data. **Not a finding:** `NSAllowsLocalNetworking` for local development hosts.
- **URL scheme and universal link handlers**: any app or web page can open a custom URL scheme, so `application(_:open:options:)`, `scene(_:openURLContexts:)` or SwiftUI `onOpenURL` code that performs an action, signs the user in or loads a URL from the parameters needs to validate them first.
- **WebView message handlers**: a `WKScriptMessageHandler` receives messages from every frame and page that the `WKWebView` loads. Report a handler that performs a native action without checking `message.frameInfo.securityOrigin` or `isMainFrame`, in a web view that can load content that the app does not control.
- **Background tasks that never end**: a `beginBackgroundTask` whose `endBackgroundTask` is not called on every path, including the expiration handler, lets the system end the app when the time runs out.

**Bad** — the completion handler runs on a background queue and updates the label there:

```swift
URLSession.shared.dataTask(with: url) { data, _, _ in
    self.statusLabel.text = data.map { String(decoding: $0, as: UTF8.self) }
}.resume()
```

**Good** — the task runs on the main actor, so the label is updated there, and a failed request is shown instead of dropped:

```swift
Task { @MainActor in
    do {
        let (data, _) = try await URLSession.shared.data(from: url)
        self.statusLabel.text = String(decoding: data, as: UTF8.self)
    } catch {
        self.statusLabel.text = "Could not load the status"
    }
}
```

## Conventions, not defects

- SwiftUI versus UIKit, MVVM versus other architectures, Combine versus async/await, and `struct` versus `final class` follow the repository's conventions.
- `guard` versus `if let`, trailing closure style and access-control spelling are style choices that SwiftLint or the repository's conventions decide.

## Sources

- Overflow and unsafe operators: https://docs.swift.org/swift-book/documentation/the-swift-programming-language/basicoperators/, https://docs.swift.org/swift-book/documentation/the-swift-programming-language/advancedoperators/
- Error handling: https://docs.swift.org/swift-book/documentation/the-swift-programming-language/errorhandling/; ARC and capture lists: https://docs.swift.org/swift-book/documentation/the-swift-programming-language/automaticreferencecounting/
- Concurrency, actors and Sendable: https://docs.swift.org/swift-book/documentation/the-swift-programming-language/concurrency/, https://github.com/swiftlang/swift-evolution/blob/main/proposals/0306-actors.md, https://www.swift.org/migration/documentation/migrationguide/
- Main thread use of UIKit: https://developer.apple.com/documentation/xcode/diagnosing-memory-thread-and-crash-issues-early
- App Transport Security: https://developer.apple.com/documentation/bundleresources/information-property-list/nsapptransportsecurity, https://developer.apple.com/documentation/security/preventing-insecure-network-connections
- Keychain: https://developer.apple.com/documentation/security/keychain-services; custom URL schemes: https://developer.apple.com/documentation/xcode/defining-a-custom-url-scheme-for-your-app
- `WKScriptMessageHandler`: https://developer.apple.com/documentation/webkit/wkscriptmessagehandler; background tasks: https://developer.apple.com/documentation/uikit/uiapplication/beginbackgroundtask(expirationhandler:)
- `JSONDecoder` and `Codable`: https://developer.apple.com/documentation/foundation/jsondecoder

## Precedents

- **Swift checks bounds and overflow**: array subscripts trap on an out-of-bounds index and arithmetic operators trap on overflow, instead of reading or writing outside the memory of the value. Do not report a buffer overflow or memory corruption for such code. **Exception:** `UnsafePointer`, `UnsafeMutableBufferPointer` and the `withUnsafe` APIs, `unsafeBitCast`, C interop, the wrapping operators such as `&+`, and builds with `-Ounchecked`; the trap itself is still a crash, reportable when input can reach it.
- **App Transport Security blocks cleartext HTTP**: on iOS 9 and later, ATS rejects `URLSession` connections that are not HTTPS with TLS 1.2 or later, unless `Info.plist` adds an exception. Do not report cleartext transport for `URLSession` requests in an app whose `Info.plist` has no ATS exception for that host. **Exception:** `NSAllowsArbitraryLoads`, `NSExceptionAllowsInsecureHTTPLoads` for the host, `NSAllowsArbitraryLoadsInWebContent` for web views, lower-level networking such as `Network.framework` connections or sockets, which ATS does not cover, and server-side Swift on Linux.
- **`Codable` decoding checks types**: `JSONDecoder` throws when a value has the wrong type or a non-optional key is missing. Do not report missing type checks for values decoded into typed `Codable` properties. **Exception:** semantic checks such as ranges, lengths, allowed values and ownership, which decoding never makes, `try?` decoding that turns errors into `nil`, custom `init(from:)` that falls back to defaults, and `[String: Any]` values from `JSONSerialization`.
- **Actors serialize access to their state**: an actor runs one synchronous section at a time, so code inside the actor never touches its stored properties concurrently. Do not report a data race on an actor's stored properties accessed from its own methods. **Exception:** reentrancy across an `await` inside an actor method, where another call can change the state between the check and the use, `nonisolated(unsafe)` properties, mutable class instances shared out of the actor through `@unchecked Sendable`, and the Swift 5 language mode with minimal concurrency checking, where non-`Sendable` values can cross isolation boundaries unchecked.
