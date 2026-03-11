# Svelte / SvelteKit — Code Review Checklist

- **Reactivity model**: reactive declarations (`$:`) used correctly; no manual DOM manipulation
- **Stores**: writable/readable/derived stores used for shared state; stores cleaned up on component destroy
- **Component props**: props declared with `export let`; default values provided where appropriate
- **SvelteKit routing**: `load` functions used for server-side data fetching; form actions used for mutations
- **SSR safety**: no browser-only APIs (`window`, `document`) accessed at module level; guarded with `browser` check
- **Transitions & animations**: built-in transition directives preferred over manual CSS class toggling
