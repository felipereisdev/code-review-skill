# React Native — Code Review Checklist

> This code runs on the user's device in the app's JavaScript engine, not on a Node.js server: Node.js modules such as `fs` and `child_process` are not available, and everything in the bundle can be read by anyone who has the app. Check sibling components for existing patterns before flagging a convention (see Consistency Check step). Report an item only with a concrete trigger → effect in the changed code. A problem that ESLint or TypeScript as configured in the repository already reports is not a finding. An item that depends on a version names the `react-native` version in `package.json`, and whether the New Architecture is enabled.

## Secrets and Storage

- **Secrets in the bundle**: API keys, client secrets or private tokens in JavaScript code, in values inlined at build time (`react-native-config`, Expo `EXPO_PUBLIC_` variables) or in `app.json` ship inside the app, where anyone can read them. Keep them on a server that makes the call. **Not a finding:** keys designed to be public whose access is enforced on the server side.
- **Token storage**: `AsyncStorage` is an unencrypted key-value store, and the React Native documentation lists tokens and secrets among what it must not hold. Use Keychain or Keystore-backed storage, such as `expo-secure-store` or `react-native-keychain`.

**Bad** — the refresh token is stored unencrypted on the device:

```js
await AsyncStorage.setItem('refreshToken', tokens.refresh);
```

**Good** — `expo-secure-store` keeps it in Keychain or Keystore-backed storage:

```js
await SecureStore.setItemAsync('refreshToken', tokens.refresh);
```

## Networking

- **`fetch` resolves on HTTP errors**: `fetch` rejects only when the request cannot be made; a `401`, `404` or `500` response resolves normally, so code that reads `response.json()` without checking `response.ok` treats an error body as data.
- **Out-of-order responses**: an effect that fetches for a changing input, such as search text or a selected id, can show the result of an older request after a newer one when the older one answers last. Ignore stale responses in the effect's cleanup, or abort them with `AbortController`.
- **Failed requests**: a request without error handling leaves the screen in its loading state, or loses the user's change, when the device is offline. Report it with that scenario; the offline caching strategy is a product choice, not a finding.
- **Cleartext traffic**: iOS App Transport Security, and Android for apps that target API level 28 or higher, block plain `http://` by default. A change that sets `NSAllowsArbitraryLoads` to `true` allows unencrypted traffic to every host in the shipped iOS build. On Android, `android:usesCleartextTraffic="true"` is ignored on Android 7.0 (API 24) and higher when a Network Security Config is present, so check that config's cleartext setting before reporting the manifest flag. Report a cleartext exception only when a release or otherwise deployed build reaches that traffic. **Not a finding:** a debug-only configuration, including the all-host debug placeholder that the React Native Gradle plugin sets for debug builds, and a development-host exception such as `localhost`.

**Bad** — a `401` or `500` error body is returned as the profile:

```js
async function loadProfile(id) {
  const response = await fetch(`${API_URL}/users/${encodeURIComponent(id)}`);
  return response.json();
}
```

**Good** — an error status becomes an error:

```js
async function loadProfile(id) {
  const response = await fetch(`${API_URL}/users/${encodeURIComponent(id)}`);
  if (!response.ok) {
    throw new Error(`profile request failed: ${response.status}`);
  }
  return response.json();
}
```

**Bad** — an older, slower search can overwrite the results of a newer one:

```js
useEffect(() => {
  searchProducts(query).then(setResults);
}, [query]);
```

**Good** — results and errors of a stale search are ignored:

```js
useEffect(() => {
  let ignore = false;
  setError(null);
  searchProducts(query)
    .then((items) => {
      if (!ignore) setResults(items);
    })
    .catch((err) => {
      if (!ignore) setError(err);
    });
  return () => {
    ignore = true;
  };
}, [query]);
```

## Deep Links, WebViews and Permissions

- **Deep links**: any app or web page can open the app's links, and another app can register the same custom scheme and receive them. Parameters from `Linking.getInitialURL()`, the `url` event or the navigation linking configuration are untrusted: a link that performs an action without the user's confirmation, such as a payment or a deletion, or that skips the sign-in check that other screens apply, is a finding, and so is a link that carries a token. OAuth redirects through a custom scheme need PKCE.
- **WebViews**: `react-native-webview` runs JavaScript by default, and its default `originWhitelist` is `['http://*', 'https://*']`. When the WebView loads a page that the user or a server controls, `onMessage` receives messages from that page, so an `onMessage` handler that performs app actions without checking `event.nativeEvent.url` lets any loaded page trigger them. Restrict navigation with `onShouldStartLoadWithRequest` or a narrower `originWhitelist`.
- **Android runtime permissions**: `PermissionsAndroid.request()` resolves to `granted`, `denied` or `never_ask_again`; code that ignores the result uses the feature without the permission, and the native call fails. On Android 13 (API level 33) and higher, `POST_NOTIFICATIONS` is a run-time permission: a non-exempt notification is not shown unless the app has requested it and the user granted it, or it was already granted. Media-session notifications are exempt, and so are notifications for self-managed calls that use `Notification.CallStyle`. On Android 12 and lower the permission does not exist, so no request is needed there. A foreground service can start without the permission; if the user denies it, the service's notice still appears in Task Manager but not in the notification drawer, so a denial hides the notice without stopping the service.

## Lists, Listeners and Native Modules

- **List keys**: a `FlatList` whose `keyExtractor` returns the index, or whose items have no `key` or `id` so that the index is used, gives rows the wrong state, such as a typed value or a swipe position, when items are inserted, removed or reordered. Return a stable id from `keyExtractor`.
- **Listener cleanup**: `AppState.addEventListener()`, `Linking.addEventListener()`, `Dimensions.addEventListener()` and `Keyboard.addListener()` return a subscription. An effect that adds one without calling `subscription.remove()` in its cleanup keeps calling the handler of a screen that is gone, and adds another listener each time the screen mounts.
- **Native module calls**: with the New Architecture, the default since React Native 0.76, native modules are called through JSI rather than the asynchronous bridge, so a native module call is not bridge overhead by itself. On the old architecture, report bridge traffic only on a hot path, such as a call per list row or per animation frame.
- **Platform-specific files**: when a component has both `Name.ios.tsx` and `Name.android.tsx` (or `.js`), a fix applied to only one of them leaves the bug on the other platform.

## Conventions, not defects

- Offline support, battery use and how native calls are batched are product and design choices; a finding needs a concrete failure, such as a crash, lost data or a leaked subscription.
- `FlatList` versus `ScrollView` follows the precedent below.
- Component and hook rules are not repeated here; this file covers what is specific to React Native.

## Sources

- Security (API keys, Async Storage, deep links, OAuth and PKCE): https://reactnative.dev/docs/security
- `react-native-config`: https://github.com/lugg/react-native-config; Expo environment variables: https://docs.expo.dev/guides/environment-variables/
- Networking: https://reactnative.dev/docs/network; `fetch` and HTTP error statuses: https://developer.mozilla.org/en-US/docs/Web/API/Window/fetch
- Stale responses in effects: https://react.dev/learn/synchronizing-with-effects#fetching-data
- App Transport Security: https://developer.apple.com/documentation/bundleresources/information-property-list/nsapptransportsecurity; Android cleartext traffic: https://developer.android.com/privacy-and-security/security-config
- `Linking`: https://reactnative.dev/docs/linking
- `react-native-webview` props: https://github.com/react-native-webview/react-native-webview/blob/master/docs/Reference.md
- `PermissionsAndroid`: https://reactnative.dev/docs/permissionsandroid; notification permission: https://developer.android.com/develop/ui/views/notifications/notification-permission
- `FlatList`: https://reactnative.dev/docs/flatlist
- `AppState`, `Keyboard`, `Dimensions`: https://reactnative.dev/docs/appstate, https://reactnative.dev/docs/keyboard, https://reactnative.dev/docs/dimensions
- New Architecture default in 0.76: https://reactnative.dev/blog/2024/10/23/the-new-architecture-is-here
- Platform-specific extensions: https://reactnative.dev/docs/platform-specific-code

## Precedents

- **`<Text>` renders strings literally**: React Native text components do not parse HTML or run scripts. Do not report XSS for user strings rendered in `<Text>` or `<TextInput>`. **Exception:** `WebView` content (`source={{ html }}`, `injectJavaScript` or a user-controlled `source.uri`), and user-controlled URLs passed to `Linking.openURL`.
- **`FlatList` and `SectionList` virtualize rows**: with their default windowing settings they keep only a window of rows around the viewport mounted, not the whole data set. Do not report a long list rendered with them as mounting every row. **Exception:** a `ScrollView` that maps over a large array, a `FlatList` nested inside a `ScrollView` with the same orientation, which breaks virtualization, settings that defeat the window (`initialNumToRender`, `maxToRenderPerBatch` or `windowSize` sized to the data, or `disableVirtualization`), and a `renderItem` or `keyExtractor` that does expensive or unbounded work per row.
