# Svelte / SvelteKit — Code Review Checklist

- **Reactivity model**: reactive declarations (`$:`) used correctly; no manual DOM manipulation
- **Stores**: writable/readable/derived stores used for shared state; stores cleaned up on component destroy
- **Component props**: props declared with `export let`; default values provided where appropriate
- **SvelteKit routing**: `load` functions used for server-side data fetching; form actions used for mutations
- **SSR safety**: no browser-only APIs (`window`, `document`) accessed at module level; guarded with `browser` check
- **Transitions & animations**: built-in transition directives preferred over manual CSS class toggling

## Precedents

- **Svelte escapes expressions**: `{expression}` in markup text and in ordinary, non-executable attribute values is escaped. Do not report XSS for user data rendered that way. **Exception:** `{@html ...}`, user-controlled URLs in `href`, `src`, `action` or `formaction`, where escaping does not stop a `javascript:` URL, user data in an `iframe` `srcdoc`, which the frame parses as a full HTML document, user strings in event-handler attributes, and user-controlled objects spread as attributes (`{...attrs}`).
- **SvelteKit checks the origin of form submissions**: with origin checking on (the default) and no trusted origin beyond the app's own sites, SvelteKit rejects cross-origin `POST`, `PUT`, `PATCH` and `DELETE` requests that have form content types. Do not report missing CSRF tokens on form actions. **Exception:** origin checking turned off (`kit.csrf.checkOrigin: false`, or `'*'` in `kit.csrf.trustedOrigins` in versions where that list replaces `checkOrigin`), `kit.csrf.trustedOrigins` entries that an attacker could control or that are broader than the app's own sites, endpoints that accept other content types such as `application/json` (protected only by CORS), and state changes on `GET` requests.
- **Private env and server modules cannot reach the client**: SvelteKit raises an error when client code imports `$env/static/private`, `$env/dynamic/private`, `$lib/server` or a `.server.ts` or `.server.js` module. Do not report those values as leaking to the browser through imports. **Exception:** data that a server `load` function or form action returns, which is serialized and sent to the browser.
