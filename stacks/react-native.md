# React Native — Code Review Checklist

- **Performance**: `FlatList`/`SectionList` used for long lists, not `ScrollView` with mapped items
- **Bridge calls**: native module calls minimized; batched where possible
- **Offline support**: app handles no-network state gracefully; critical data cached locally
- **Deep links**: deep link handlers validated and sanitized before use
- **Platform-specific code**: `Platform.OS` checks or `.ios.js`/`.android.js` extensions used correctly
- **Battery & memory**: background tasks, location, and camera usage minimized and released when not needed

## Precedents

- **`<Text>` renders strings literally**: React Native text components do not parse HTML or run scripts. Do not report XSS for user strings rendered in `<Text>` or `<TextInput>`. **Exception:** `WebView` content (`source={{ html }}`, `injectJavaScript` or a user-controlled `source.uri`), and user-controlled URLs passed to `Linking.openURL`.
- **`FlatList` and `SectionList` virtualize rows**: with their default windowing settings they keep only a window of rows around the viewport mounted, not the whole data set. Do not report a long list rendered with them as mounting every row. **Exception:** a `ScrollView` that maps over a large array, a `FlatList` nested inside a `ScrollView` with the same orientation, which breaks virtualization, settings that defeat the window (`initialNumToRender`, `maxToRenderPerBatch` or `windowSize` sized to the data, or `disableVirtualization`), and a `renderItem` or `keyExtractor` that does expensive or unbounded work per row.
