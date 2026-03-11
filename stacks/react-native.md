# React Native — Code Review Checklist

- **Performance**: `FlatList`/`SectionList` used for long lists, not `ScrollView` with mapped items
- **Bridge calls**: native module calls minimized; batched where possible
- **Offline support**: app handles no-network state gracefully; critical data cached locally
- **Deep links**: deep link handlers validated and sanitized before use
- **Platform-specific code**: `Platform.OS` checks or `.ios.js`/`.android.js` extensions used correctly
- **Battery & memory**: background tasks, location, and camera usage minimized and released when not needed
