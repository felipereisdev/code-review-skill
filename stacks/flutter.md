# Flutter — Code Review Checklist

> Check sibling widgets for existing patterns before flagging a convention (see Consistency Check step). Report an item only with a concrete trigger → effect in the changed code. A problem that `flutter analyze` with the repository's `analysis_options.yaml` already reports, such as `use_build_context_synchronously` or `prefer_const_constructors`, is not a finding. An item that depends on a version names the Flutter or Dart SDK version that it needs; read the `environment` section of `pubspec.yaml`.

## Async Work and the Widget Lifecycle

- **`BuildContext` after `await`**: using `context` after an `await` in a `State` method, for example `Navigator.of(context)` or `ScaffoldMessenger.of(context)`, can act on a widget that was removed while the future ran: it navigates from the wrong screen or throws. After the `await`, check `if (!mounted) return;` in a `State`, or `context.mounted` (Flutter 3.7+) elsewhere.
- **`setState()` after `dispose()`**: a future, timer or stream callback that calls `setState()` after its `State` was disposed throws. Check `mounted`, or cancel the timer or subscription in `dispose()`.
- **Resources owned by a `State`**: an `AnimationController`, `TextEditingController`, `ScrollController`, `FocusNode`, `StreamSubscription` or `Timer` that a `State` creates must be disposed or cancelled in its `dispose()`; otherwise its listeners, tickers or callbacks keep running after the screen is gone. **Not a finding:** a controller passed in by a parent that owns and disposes it.
- **Futures created in `build()`**: `FutureBuilder(future: api.load(), ...)` creates a new future, and sends a new request, on every rebuild, such as when the keyboard opens or a parent calls `setState()`. Create the future once, in `initState()` or a `late final` field (and again in `didUpdateWidget()` when its input changes), and keep it in the `State`. The same holds for a `StreamBuilder` stream.
- **Missing error and loading states**: a `FutureBuilder` or `StreamBuilder` builder that reads `snapshot.data!` without checking `hasError` and `hasData` throws on the first frame and on every error.

**Bad** — navigates after the widget may have been removed:

```dart
Future<void> _save() async {
  await repository.save(form);
  Navigator.of(context).pop();
}
```

**Good** — stops when the widget is no longer mounted:

```dart
Future<void> _save() async {
  await repository.save(form);
  if (!mounted) return;
  Navigator.of(context).pop();
}
```

**Bad** — starts a new request on every rebuild and throws while it loads or when it fails:

```dart
class OrdersPage extends StatelessWidget {
  const OrdersPage({super.key, required this.api});
  final OrdersApi api;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Order>>(
      future: api.loadOrders(),
      builder: (context, snapshot) => OrderList(orders: snapshot.data!),
    );
  }
}
```

**Good** — creates the future once and handles the error and loading states:

```dart
class OrdersPage extends StatefulWidget {
  const OrdersPage({super.key, required this.api});
  final OrdersApi api;

  @override
  State<OrdersPage> createState() => _OrdersPageState();
}

class _OrdersPageState extends State<OrdersPage> {
  late final Future<List<Order>> _orders = widget.api.loadOrders();

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Order>>(
      future: _orders,
      builder: (context, snapshot) {
        if (snapshot.hasError) return ErrorView(error: snapshot.error!);
        if (!snapshot.hasData) return const CircularProgressIndicator();
        return OrderList(orders: snapshot.data!);
      },
    );
  }
}
```

## Lists, Keys and Performance

- **Long lists**: `ListView(children: ...)`, or a `Column` inside a `SingleChildScrollView`, builds every item at once; for a long or unbounded list, `ListView.builder` builds only the items that are visible. **Not a finding:** a short list whose length the code bounds.
- **Keys for stateful items**: when a list of stateful items, such as rows with text fields, checkboxes or animations, can be reordered, filtered, or have items inserted or removed, items without keys keep their `State` by position, so state moves to the wrong item. Give each item a key from its identity, such as `ValueKey(item.id)`. **Not a finding:** stateless items, and lists that only ever append.
- **Heavy work on the UI isolate**: decoding a large JSON payload, processing images or hashing large data on the main isolate drops frames. Move it to `compute()` or `Isolate.run()` (Dart 2.19+). **Not a finding:** small payloads whose size the code bounds.

## Platform Channels and Plugins

- **Platform errors**: `MethodChannel.invokeMethod` throws `PlatformException` when the native side reports an error, and `MissingPluginException` when no handler is registered for the channel, for example on a platform that the plugin does not support. An uncaught one fails the action with no feedback to the user.
- **Untyped results**: platform channel results and `jsonDecode()` return `dynamic`, and maps from a platform channel arrive as `Map<Object?, Object?>`, so `result as Map<String, dynamic>` throws a `TypeError` at run time. Use `invokeMapMethod<String, dynamic>()` or `Map<String, dynamic>.from(...)`, and check field types before casting.
- **Before the binding exists**: a plugin or platform channel called in `main()` before `WidgetsFlutterBinding.ensureInitialized()` and before `runApp()` throws, because the binding that carries platform messages does not exist yet.

## Security and Data

- **Secrets in the app**: API keys, client secrets or signing keys in Dart code, in assets or in `--dart-define` values ship inside the app and can be extracted from it; `--obfuscate` only renames symbols. Keep secrets on a server. **Not a finding:** keys designed to be public whose access is enforced on the server side, such as Firebase API keys.
- **Tokens in `shared_preferences`**: `shared_preferences` wraps `NSUserDefaults` and Android `SharedPreferences`, which are not encrypted storage, and its documentation says that it must not be used for critical data. Store auth tokens and secrets in Keychain or Keystore-backed storage.
- **URLs from untrusted sources**: a URL from a deep link, a server response or user input that is passed to `launchUrl()` or loaded into a WebView can open any scheme or host that the platform handles; check the scheme and host first. A WebView with `JavaScriptMode.unrestricted` and a JavaScript channel (`addJavaScriptChannel`) that loads third-party or user-controlled pages lets those pages call into the app.
- **Deep link routes**: route parameters from a deep link are attacker-controlled, because any app or web page can open the link. A route that performs an action, such as a payment or a deletion, without confirmation, or that skips the sign-in check that other routes apply, is a finding.

## Conventions, not defects

- `const` constructors and splitting large `build()` methods are analyzer lints or Suggestions (Code & File Size governs length); they are never findings by themselves.
- The state management solution (Provider, Riverpod, Bloc, or `setState()` for local state) follows the project's established choice; a finding needs state that is lost, stale or shared incorrectly in a concrete scenario.
- Calling an async platform method from `initState()` is allowed; handling its result follows the `mounted` rule above.

## Sources

- `State.mounted`, `setState()` and `dispose()`: https://api.flutter.dev/flutter/widgets/State-class.html
- `BuildContext.mounted` and the lint: https://api.flutter.dev/flutter/widgets/BuildContext/mounted.html, https://dart.dev/tools/linter-rules/use_build_context_synchronously
- `FutureBuilder` and `StreamBuilder`: https://api.flutter.dev/flutter/widgets/FutureBuilder-class.html, https://api.flutter.dev/flutter/widgets/StreamBuilder-class.html
- `ListView.builder`: https://api.flutter.dev/flutter/widgets/ListView-class.html
- Keys: https://api.flutter.dev/flutter/foundation/Key-class.html, https://api.flutter.dev/flutter/widgets/Widget/key.html
- Isolates: https://docs.flutter.dev/perf/isolates
- Platform channels: https://docs.flutter.dev/platform-integration/platform-channels, https://api.flutter.dev/flutter/services/MethodChannel-class.html
- `WidgetsFlutterBinding.ensureInitialized()`: https://api.flutter.dev/flutter/widgets/WidgetsFlutterBinding/ensureInitialized.html
- Obfuscation: https://docs.flutter.dev/deployment/obfuscate
- Firebase API keys: https://firebase.google.com/docs/projects/api-keys
- `shared_preferences`: https://pub.dev/packages/shared_preferences
- `url_launcher` and `webview_flutter`: https://pub.dev/packages/url_launcher, https://pub.dev/packages/webview_flutter

## Precedents

- **Sound null safety rules out null**: a variable with a non-nullable type cannot hold `null`. Do not report a missing null check on it. **Exception:** the `!` operator, `late` variables read before assignment, values from `dynamic`, JSON decoding or platform channels cast with `as`, and code that runs without sound null safety, such as files with a `// @dart=2.9` or older language-version comment, projects whose SDK lower bound is below 2.12, and builds run with `--no-sound-null-safety`.
- **`Text` widgets render strings literally**: `Text`, `RichText` and `TextField` do not parse HTML or run scripts. Do not report XSS for user strings shown in them. **Exception:** HTML loaded into a WebView (`loadHtmlString`, `runJavaScript`) or rendered by an HTML widget package, and user-controlled URLs opened with `url_launcher`.
