# Flutter — Code Review Checklist

- **Widget tree**: large `build` methods split into smaller widgets; `const` constructors used where possible
- **State management**: state management solution (Provider, Riverpod, Bloc) used consistently; no `setState` for global state
- **Async widgets**: `FutureBuilder`/`StreamBuilder` handle loading and error states explicitly
- **Platform channels**: platform channel calls are async and handle errors; not called from `initState`
- **Memory**: images sized appropriately; `dispose()` called on controllers (animation, text, scroll)
