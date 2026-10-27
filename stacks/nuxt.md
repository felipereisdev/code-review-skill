# Nuxt.js — Code Review Checklist

> These items are about Nuxt 3 and Nuxt 4 applications; read the version from `package.json` or the lockfile. Code in `server/` runs only in the Nitro server. Pages, components, composables, plugins and route middleware run on the server while it renders a page and again in the browser. Check sibling files for existing patterns before flagging a convention (see Consistency Check step). Report an item only with a concrete trigger → effect in the changed code. A problem that `nuxi typecheck`, ESLint or TypeScript as configured in the repository already reports is not a finding.

## Server Routes and Request State

- **API routes behind route middleware only**: route middleware (the `middleware/` directory, `addRouteMiddleware`, `definePageMeta({ middleware })`) runs in the Vue part of the app before page navigations. It is not Nitro server middleware and does not run for requests to `server/api/` or `server/routes/` handlers, so an API route that returns or changes private data and relies on a page's route middleware for authentication answers anyone who calls its URL. Check the session in the handler, or in server middleware (`server/middleware/`) that rejects the request. **Not a finding:** handlers that a server middleware or the handler itself already protects, and endpoints meant to be public.
- **Module-level state in server code**: the server loads each module once and serves every request with the same module instances, so a module-level variable that server middleware or a handler sets from one request (the current user, tenant or locale) is read by other requests that run at the same time or later. Keep per-request values on `event.context`. **Not a finding:** module-level values that never hold per-request data, such as a database pool or a cache of public data.
- **`$fetch` during server rendering**: on the server, `$fetch('/api/...')` called from a component, composable or plugin does not send the browser's cookies, so an API route that authenticates by cookie answers as if the user were signed out, and the server-rendered page shows that answer. `useFetch` with a relative URL forwards the request's headers and cookies by itself (through `useRequestFetch`); for `$fetch`, use the function that `useRequestFetch()` returns. **Not a finding:** `$fetch` that runs only in the browser, such as in a click handler, which sends the cookies of a same-origin request.

**Bad** — the invoices page uses `definePageMeta({ middleware: 'auth' })`, but this route returns every invoice to anyone who calls `/api/invoices`:

```js
// server/api/invoices.get.js
import { db } from '../utils/db.js';

export default defineEventHandler(async () => {
  return await db.invoice.findMany();
});
```

**Good** — the handler checks the session and returns only the caller's invoices:

```js
// server/api/invoices.get.js
import { db } from '../utils/db.js';
import { requireUser } from '../utils/session.js';

export default defineEventHandler(async (event) => {
  const user = await requireUser(event); // throws a 401 error without a valid session
  return await db.invoice.findMany({ where: { ownerId: user.id } });
});
```

**Bad** — one variable holds the user of whichever request ran the middleware last:

```js
// server/middleware/user.js
import { readSession } from '../utils/session.js';

let currentUser = null;

export default defineEventHandler(async (event) => {
  currentUser = await readSession(event);
});

export function getCurrentUser() {
  return currentUser;
}
```

**Good** — each request carries its own user, which handlers read from `event.context.user`:

```js
// server/middleware/user.js
import { readSession } from '../utils/session.js';

export default defineEventHandler(async (event) => {
  event.context.user = await readSession(event);
});
```

## Data Fetching and Hydration

- **URLs built once**: `useFetch(`/api/orders?page=${page.value}`)` builds the URL when the call runs, so a later change to `page` keeps fetching the first page; the `watch` option runs the request again but does not change the URL. Pass reactive values in `query` or `params`, which `useFetch` watches, or pass the URL as a getter or a computed value.
- **One key for different data**: `useAsyncData` and `useFetch` calls with the same key share the same `data`, `error` and `status`, and their handler and other data options must be the same. Two calls that use one explicit key for different requests, such as `useAsyncData('user', ...)` for the signed-in user and for a profile that the page shows, overwrite each other's data. **Not a finding:** identical calls that share a key on purpose to share one result.
- **Composables after an `await` during server rendering**: Nuxt composables (`useFetch`, `useAsyncData`, `useState`, `useRuntimeConfig`, `useNuxtApp`, `useRequestFetch` and others) find the Nuxt instance through a context that the server sets while it runs setup, a plugin or route middleware. Without native async context, a composable called after an `await` in an ordinary async function, or in a function that such code calls, finds no instance and fails with a `Nuxt instance is unavailable` error, unless that call itself runs inside `nuxtApp.runWithContext(...)` or `callWithNuxt(...)`, which restore the instance for the call with or without the flag. A wrapper around a whole async callback does not automatically cover a call that comes after that callback's own `await`. **Not a finding:** an `await` before the composable directly in `<script setup>`, in the setup of `defineNuxtComponent`, in `defineNuxtPlugin` or in `defineNuxtRouteMiddleware`, where Nuxt's compiler transform or Vue's `await` handling keeps the context across the `await` without any flag; and, with `experimental.asyncContext` enabled (the flag exists in the Nuxt 3.21 and 4.6 sources) on a server runtime that provides `AsyncLocalStorage` (Nitro's renderer adds one when the flag is on and none exists), a composable after an `await` in a chain that started inside one of Nuxt's server runners: a plugin, route middleware, a hook called with `callHook`, the setup or legacy `asyncData` option of `defineNuxtComponent`, or the top-level `await` expression of `<script setup>`. The context then follows that chain through the functions it calls and their own later `await`s. The flag does not cover a chain that starts outside those runners, so check where the chain starts, not only the flag: a composable call after an `await` in a callback given to `onServerPrefetch`, in an async function that `<script setup>` calls without a top-level `await`, or in a timer or promise created there fails unless the call runs inside a Nuxt runner or an explicit `runWithContext` or `callWithNuxt` restoration, with or without the flag. In the browser, the Nuxt instance stays set once the app has started, so `useRuntimeConfig()` or `useState()` in a click handler or timer does not fail with this error. Two conditions still apply there: `useFetch` and `useAsyncData` called after mount emit the development diagnostic `NUXT_E3003`, and Vue's own `inject()` and lifecycle hooks need a component setup. The docs recommend `$fetch` for requests started by user events.
- **Markup that differs between server and browser**: rendering `Date.now()`, `Math.random()`, a date formatted in the local time zone or locale, or a branch on `import.meta.client` or `window` produces different HTML on the server and in the browser. Vue then discards and re-creates the mismatched nodes, which costs rendering time and changes the content that the user already sees. Render such parts after mounting (`onMounted`, `<ClientOnly>`), or compute the value once on the server and transfer it with `useState`.

**Bad** — changing `page` never changes the URL, so the list stays on page 1:

```js
// <script setup> of a paginated list
const page = ref(1);
const { data: orders } = await useFetch(`/api/orders?page=${page.value}`);
```

**Good** — `useFetch` watches the reactive `query` and fetches again when `page` changes:

```js
// <script setup> of a paginated list
const page = ref(1);
const { data: orders } = await useFetch('/api/orders', { query: { page } });
```

## Runtime Configuration

- **Defaults from differently named variables**: at runtime, Nuxt overrides a `runtimeConfig` value only from an environment variable named `NUXT_` plus the key in upper snake case (`NUXT_API_SECRET` for `apiSecret`, `NUXT_PUBLIC_API_BASE` for `public.apiBase`). A default read from a variable with another name (`apiSecret: process.env.API_SECRET`) is read only during the build, so setting `API_SECRET` on the production server changes nothing and the app keeps the build environment's value. Set the value through the `NUXT_` variable instead.

## Conventions, not defects

- `useState` or Pinia, auto-imports or explicit imports, and `<ClientOnly>` or `onMounted` follow the app's existing choices; none of them is a finding by itself.
- `$fetch` in component setup instead of `useFetch` or `useAsyncData` is a finding only through an effect described here or in the Precedents, such as a second request after hydration or a missing cookie on the server.

## Sources

- Data fetching (`useFetch`, `useAsyncData`, keys, reactive options, cookies on the server): https://nuxt.com/docs/4.x/getting-started/data-fetching
- Composables and the Nuxt context: https://nuxt.com/docs/4.x/guide/concepts/auto-imports
- Experimental `asyncContext` option: https://nuxt.com/docs/4.x/guide/going-further/experimental-features
- Nuxt server context runners, `runWithContext` and `callWithNuxt`, and the compiler transform (source at v4.6.3): https://github.com/nuxt/nuxt/tree/v4.6.3/packages/nuxt/src
- Route middleware: https://nuxt.com/docs/4.x/directory-structure/app/middleware
- Server routes, server middleware and `event.context`: https://nuxt.com/docs/4.x/directory-structure/server
- Runtime config and `NUXT_` variables: https://nuxt.com/docs/4.x/guide/going-further/runtime-config
- Hydration mismatches and cross-request state: https://vuejs.org/guide/scaling-up/ssr.html

## Precedents

- **`useFetch` and `useAsyncData` reuse server data on hydration**: a value that the handler returns during server rendering is stored in the page payload under the call's key (unless it is `serialize: false`), and the client call with the same key reads it instead of fetching again. Do not report them as fetching twice. **Exception:** a handler that returns `undefined` or `null` (for example one that forgets `return`), a key or options that differ between server and client (for example a key built from `Date.now()` or `Math.random()`), `serialize: false` or other payload stripping, which keeps the value out of the payload so the client fetches it again, a custom `getCachedData` that returns `undefined`, and `$fetch` called directly in component setup, which runs on the server and again on the client.
- **`useState` gives each request its own state slot**: `useState(key, init)` keeps its value in the payload of the current server request and transfers it to the client, so each request gets a separate slot; it stores the result of `init` as is and does not clone it. Do not report it as leaking state between users when `init` allocates fresh data on every call (for example `() => ({ userId: null })`). **Exception:** an `init` that returns an object or array shared across calls, such as a module-scope constant, a cached value or a factory that returns the same instance, where mutating a nested property through `.value` changes the shared object for every later request, `ref` or `reactive` values declared at module scope (outside any function, for example at the top of a composable file), which the server shares across all requests, and other module-scope objects, arrays or caches that request code writes to.
- **Private `runtimeConfig` stays out of the client bundle**: keys outside the `public` and `app` namespaces of `runtimeConfig` are only available in the server bundle and in `server/` code such as API routes, server middleware and Nitro plugins, never in the client JavaScript. Do not report them as exposed to the browser through the client bundle. **Exception:** keys under `runtimeConfig.public` or `runtimeConfig.app`, which both reach the client, private keys read in a component, composable or page, which also runs on the server during SSR, where `useRuntimeConfig()` returns the entire config including private keys, so a value rendered into the template or serialized into the HTML or payload reaches the browser, and private values that server code returns from an API route or puts into `useState` or the payload.
