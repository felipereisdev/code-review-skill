# Svelte / SvelteKit — Code Review Checklist

> Check sibling components and routes for existing patterns before flagging a convention (see Consistency Check step). Report an item only with a concrete trigger → effect in the changed code. A problem that `svelte-check`, ESLint or TypeScript as configured in the repository already reports is not a finding. Svelte 5 compiles a component in runes mode when it uses runes (`$state`, `$derived`, `$effect`, `$props`) or the `runes: true` compiler option, and in legacy mode otherwise; Svelte 3 and 4 components are always in legacy mode. Read the Svelte and SvelteKit versions from `package.json` or the lockfile, and the mode from the component itself, before applying an item that names one. Apply the SvelteKit items only when the package declares `@sveltejs/kit`.

## Reactivity

- **Mutations in legacy mode**: legacy-mode reactivity is based on assignments, so `items.push(x)`, `items.splice(i, 1)`, or a mutation through an alias or a function parameter that the compiler cannot tie to the component's variable, leaves the markup and every `$:` statement that reads `items` stale unless an assignment to `items` follows. A property or item assignment to the component variable, even inside a function (`items[i].done = true`), is tracked and needs no extra assignment. A `$:` statement depends only on the values that appear directly in it, not on the values read by a function that it calls. **Not a finding:** runes mode, where an array or plain object in `$state` is a deep proxy and `push` updates the UI, a mutation followed by an assignment (`items = items`), and a direct property or item assignment to the component variable inside a function.
- **Copies of runes state**: in runes mode, destructuring a `$state` object (`let { count } = counter`) or passing a `$state` value to a function copies its current value, and the copy does not change when the state does. Pass the object, or a getter function, when the receiver must see later changes.
- **Reads after `await` in `$effect`**: an effect tracks only the reactive values that it reads synchronously. A value read after an `await` or inside a `setTimeout` callback is not a dependency, so the effect does not run again when it changes. Read it before the first `await`.

## Lifecycle and Cleanup

- **Cleanup returned from an `async` `onMount`**: Svelte calls the function that an `onMount` callback returns when the component unmounts, but only when the callback is synchronous. An `async` callback returns a promise, so the interval, listener, socket or subscription that its returned function was meant to remove stays active after the component is destroyed, and every new instance of the component adds one more. Start the async work from a synchronous callback and return the cleanup from it. **Not a finding:** an `async` `onMount` that starts nothing that needs cleanup.
- **Effects and manual subscriptions**: an `$effect` that adds a listener, timer or subscription needs to return a teardown function, which Svelte runs before the effect runs again and when the component is destroyed; without it, every run adds another. A manual `store.subscribe(...)` returns an unsubscribe function that the component must call when it is destroyed. **Not a finding:** a store read with the `$store` prefix in a component, which Svelte subscribes and unsubscribes by itself.
- **Browser APIs during server rendering**: with server-side rendering on (the SvelteKit default), a component's `<script>` also runs on the server, so a top-level reference to `window`, `document` or `localStorage` throws a `ReferenceError` there and the request fails. `onMount` and `$effect` never run on the server, but `onDestroy` does, so the same reference in `onDestroy` also throws. **Not a finding:** such code inside `onMount` or `$effect`, behind a check of `browser` (from `$app/environment`, or `$app/env` in SvelteKit 3), or in a route that sets `export const ssr = false`.

**Bad** — in a component's `<script>`, the returned cleanup is ignored because the callback is `async`, so the interval keeps running after the component is destroyed:

```js
import { onMount } from 'svelte';
import { loadConfig, refresh } from './dashboard.js';

onMount(async () => {
  const config = await loadConfig();
  const timer = setInterval(() => refresh(config), 5000);
  return () => clearInterval(timer);
});
```

**Good** — the callback is synchronous, and the cleanup also covers a component destroyed before `loadConfig()` resolves:

```js
import { onMount } from 'svelte';
import { loadConfig, refresh } from './dashboard.js';

onMount(() => {
  let timer;
  let destroyed = false;
  loadConfig().then((config) => {
    if (!destroyed) timer = setInterval(() => refresh(config), 5000);
  });
  return () => {
    destroyed = true;
    clearInterval(timer);
  };
});
```

## SvelteKit Server Code

- **State shared between requests**: the server loads each module once and uses it for every request. A module-level variable, or a store created at module scope, that a `load` function, form action or hook fills with one user's data is visible to other users' requests. Return the data from `load`, keep per-request values in `event.locals`, and give components shared state through `setContext`. **Not a finding:** module-level values that never hold per-user data, such as configuration or a cache of public data.
- **Authorization only in a layout**: a check placed only in a `+layout.server.js` `load` does not protect its child routes. Layout `load` functions do not run again on client-side navigation between child routes, run in parallel with page `load` functions unless the page awaits `parent()`, and do not run before a form action, which runs first and is followed by the page's `load` functions. Check the user in the `handle` hook of `hooks.server.js`, or in each `+page.server.js` `load`, form action and `+server.js` handler that returns or changes protected data.
- **`redirect()` or `error()` inside `try`**: both helpers throw (code for SvelteKit 1 writes `throw redirect(...)` itself), so inside a `try` block whose `catch` handles every error, the `catch` swallows the redirect or the error response and runs its own code instead. Call them after the `try` block, or rethrow when `isRedirect(e)` or `isHttpError(e)` is true.
- **`fetch` in universal `load`**: `+page.js` and `+layout.js` `load` functions run on the server for the first request and in the browser afterwards. On the server, the global `fetch` cannot request a relative URL and does not send the user's cookies. Use the `fetch` that `load` receives: it accepts relative URLs on the server, forwards the page request's `cookie` and `authorization` headers, and inlines the response into the HTML so that hydration does not request it again.
- **Whole records returned to the page**: everything that a server `load` function returns is serialized and sent to the browser. Returning whole database rows sends every column, such as password hashes, tokens or internal notes, to anyone who can open the page. Return only the fields that the page uses.

**Bad** — `user` is shared by every request, and the action runs before any `load`, so it can update another visitor's profile:

```js
import { getUserFromSession, updateProfile } from '../../lib/server/account.js';

let user;

export async function load({ cookies }) {
  user = await getUserFromSession(cookies.get('session'));
  return { email: user?.email };
}

export const actions = {
  default: async ({ request }) => {
    await updateProfile(user.id, await request.formData());
  }
};
```

**Good** — every `load` and action reads the user of its own request:

```js
import { fail } from '@sveltejs/kit';
import { getUserFromSession, updateProfile } from '../../lib/server/account.js';

export async function load({ cookies }) {
  const user = await getUserFromSession(cookies.get('session'));
  return { email: user?.email };
}

export const actions = {
  default: async ({ cookies, request }) => {
    const user = await getUserFromSession(cookies.get('session'));
    if (!user) return fail(401);
    await updateProfile(user.id, await request.formData());
  }
};
```

**Bad** — the `catch` block also catches the redirect, so a created order answers with the failure message:

```js
import { fail, redirect } from '@sveltejs/kit';
import { createOrder } from '../../lib/server/orders.js';

export const actions = {
  default: async ({ request }) => {
    try {
      const order = await createOrder(await request.formData());
      redirect(303, `/orders/${order.id}`);
    } catch {
      return fail(500, { message: 'Could not create the order' });
    }
  }
};
```

**Good** — the redirect runs after the `try` block:

```js
import { fail, redirect } from '@sveltejs/kit';
import { createOrder } from '../../lib/server/orders.js';

export const actions = {
  default: async ({ request }) => {
    let order;
    try {
      order = await createOrder(await request.formData());
    } catch {
      return fail(500, { message: 'Could not create the order' });
    }
    redirect(303, `/orders/${order.id}`);
  }
};
```

## Conventions, not defects

- Runes or legacy syntax, stores or `$state` in classes, and `export let` or `$props()` follow the package's Svelte version and its existing components. The choice is not a finding; a mode-specific bug from the items above is.
- Built-in transitions instead of CSS classes, form actions instead of `+server.js` endpoints, and where data loading lives are design choices; they are findings only through a concrete bug, such as the authorization and shared-state items above.

## Sources

- Runes and legacy mode: https://svelte.dev/docs/svelte/legacy-overview; assignment-based updates: https://svelte.dev/docs/svelte/legacy-let; `$:` dependencies: https://v4.svelte.dev/docs/svelte-components
- `$state`: https://svelte.dev/docs/svelte/$state; `$effect`: https://svelte.dev/docs/svelte/$effect
- `onMount`, `onDestroy`: https://svelte.dev/docs/svelte/lifecycle-hooks; stores: https://svelte.dev/docs/svelte/stores
- `browser`: https://svelte.dev/docs/kit/$app-environment, https://svelte.dev/docs/kit/$app-env; `ssr`: https://svelte.dev/docs/kit/page-options
- Shared server state and pure `load` functions: https://svelte.dev/docs/kit/state-management
- `load`, authentication, `fetch`, `redirect`: https://svelte.dev/docs/kit/load; form actions: https://svelte.dev/docs/kit/form-actions
- `handle` and `event.locals`: https://svelte.dev/docs/kit/hooks; `isRedirect`, `isHttpError`: https://svelte.dev/docs/kit/@sveltejs-kit

## Precedents

- **Svelte escapes expressions**: `{expression}` in markup text and in ordinary, non-executable attribute values is escaped. Do not report XSS for user data rendered that way. **Exception:** `{@html ...}`, user-controlled URLs in `href`, `src`, `action` or `formaction`, where escaping does not stop a `javascript:` URL, user data in an `iframe` `srcdoc`, which the frame parses as a full HTML document, user strings in event-handler attributes, and user-controlled objects spread as attributes (`{...attrs}`).
- **SvelteKit checks the origin of form submissions**: with origin checking on (the default) and no trusted origin beyond the app's own sites, SvelteKit rejects cross-origin `POST`, `PUT`, `PATCH` and `DELETE` requests that have form content types. Do not report missing CSRF tokens on form actions. **Exception:** origin checking turned off (`kit.csrf.checkOrigin: false`, or `'*'` in `kit.csrf.trustedOrigins` in versions where that list replaces `checkOrigin`), `kit.csrf.trustedOrigins` entries that an attacker could control or that are broader than the app's own sites, endpoints that accept other content types such as `application/json` (protected only by CORS), and state changes on `GET` requests.
- **Private env and server modules cannot reach the client**: SvelteKit raises an error when client code imports `$env/static/private`, `$env/dynamic/private`, `$lib/server` or a `.server.ts` or `.server.js` module. Do not report those values as leaking to the browser through imports. **Exception:** data that a server `load` function or form action returns, which is serialized and sent to the browser.
