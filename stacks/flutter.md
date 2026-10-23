# Flutter — Code Review Checklist

- **Widget tree**: large `build` methods split into smaller widgets; `const` constructors used where possible
- **State management**: state management solution (Provider, Riverpod, Bloc) used consistently; no `setState` for global state
- **Async widgets**: `FutureBuilder`/`StreamBuilder` handle loading and error states explicitly
- **Platform channels**: platform channel calls are async and handle errors; not called from `initState`
- **Memory**: images sized appropriately; `dispose()` called on controllers (animation, text, scroll)

## Precedents

- **Sound null safety rules out null**: a variable with a non-nullable type cannot hold `null`. Do not report a missing null check on it. **Exception:** the `!` operator, `late` variables read before assignment, and values from `dynamic`, JSON decoding or platform channels cast with `as`.
- **`Text` widgets render strings literally**: `Text`, `RichText` and `TextField` do not parse HTML or run scripts. Do not report XSS for user strings shown in them. **Exception:** HTML loaded into a WebView (`loadHtmlString`, `runJavaScript`) or rendered by an HTML widget package, and user-controlled URLs opened with `url_launcher`.
