# Next.js — Code Review Checklist

> Check sibling routes and components for existing patterns before flagging a convention (see Consistency Check step). Report an item only with a concrete trigger → effect in the changed code. A problem that ESLint, TypeScript or the Next.js build, as the repository configures them, already reports is not a finding. This file covers what Next.js adds: Server Actions, Route Handlers, middleware, rendering and caching, and what crosses from the server to the browser. React component rules come from `./stacks/react.md`, which applies to the React code of the change as the package's `react` dependency proves. Read the Next.js version from `package.json` or the lockfile, and the router from the files the change touches: `app/` for the App Router, `pages/` for the Pages Router. An item that names a version or a router applies only to it.

## Server Actions and Route Handlers

- **Server Actions are public endpoints**: an exported function in a `'use server'` file, or an inline action, can be called with a `POST` request by anyone who has its ID, whether or not the UI shows the form or button that uses it. Report an action that reads or changes data without checking, inside the action, who the caller is and whether they may act on that record. Arguments arrive from the client: a TypeScript type is not a runtime check, so validate them.
- **Route Handlers need their own checks**: an exported `GET`, `POST`, `PUT`, `PATCH` or `DELETE` in `app/**/route.ts`, or a Pages Router API route, runs for every request that reaches its path. Report a handler that relies only on the page that calls it, or only on middleware whose `matcher` does not cover its path, for authentication or authorization.
- **Authorization only in middleware**: middleware (renamed `proxy` in Next.js 16) runs before routes, but the Next.js documentation recommends checking access again next to the data, because a matcher can miss a path and middleware does not run for every way of reaching data. Versions before 12.3.5, 13.5.9, 14.2.25 and 15.2.3 let a request skip middleware with the `x-middleware-subrequest` header (CVE-2025-29927). Report a change whose only access check is in middleware on an affected version, or for a path its matcher excludes.

**Bad** — anyone who calls the action can delete any invoice:

```js
'use server'
import { db } from '@/lib/db'

export async function deleteInvoice(id) {
  await db.invoice.delete({ where: { id } })
}
```

**Good** — the action checks the session and the owner before it deletes:

```js
'use server'
import { db } from '@/lib/db'
import { getSession } from '@/lib/session'

export async function deleteInvoice(id) {
  const session = await getSession()
  if (!session) throw new Error('Not signed in')
  await db.invoice.deleteMany({ where: { id: String(id), ownerId: session.userId } })
}
```

## Server and Client Boundary

- **Server data sent to the browser**: props passed from a Server Component to a Client Component, and values that a Server Action returns, are serialized into the page or the response that the browser receives. Report a change that passes a whole record, such as a user row with its password hash, tokens or another user's data, where the client needs a few fields. Import `server-only` in modules that hold secrets or database access, so that a client import fails the build.
- **Public environment variables**: a variable whose name starts with `NEXT_PUBLIC_` is inlined into the browser bundle at build time. Report a secret given that prefix, or a value that the code expects to change at runtime but that the build already fixed. **Not a finding:** non-prefixed variables read only in server code.

## Caching and Rendering

- **Per-user data in a shared cache**: data fetched with `cache: 'force-cache'`, `next: { revalidate }`, `unstable_cache` or `'use cache'` is shared by every request with the same cache key. Report user-specific data cached under a key that does not include the user, and a page rendered statically (`dynamic = 'force-static'`, or a page that reads no request data) that shows per-user content. In Next.js 14 and earlier, `fetch` in Server Components was cached by default; from Next.js 15 it is not.
- **Stale pages after a change**: a Server Action or Route Handler that changes data shown by a cached page or a cached fetch, without `revalidatePath` or `revalidateTag` (or `updateTag` in Next.js 16), leaves the old data on screen for other users until the cache expires. **Not a finding:** pages rendered dynamically for each request.
- **Request APIs in Next.js 15 and later**: `cookies()`, `headers()`, `draftMode()`, and the `params` and `searchParams` props are asynchronous from Next.js 15. Synchronous access still works with a warning in Next.js 15 and is removed in Next.js 16; report it in a change for Next.js 16, where it no longer works as before.

## Redirects and Images

- **Open redirects**: `redirect(searchParams.next)` or `NextResponse.redirect(new URL(next, request.url))` with a value from the request sends the user to any site, because `new URL()` ignores the base URL when the value is absolute (`https://evil.example`) or protocol-relative (`//evil.example`). A check on the raw text is not enough: the URL parser removes ASCII tab and newline characters before it reads the value, so the encoded value `%2F%09%2Fevil.example` (decoded: `/`, a tab, `/evil.example`) becomes the protocol-relative `//evil.example`. Parse the value against the request URL, and redirect only when the parsed origin is the request's own origin; send anything else, including a value that does not parse, to `/`.
- **Image optimizer for broad remote patterns**: an `images.remotePatterns` entry with a wildcard `hostname`, such as `'**'`, lets the default optimizer at `/_next/image` fetch and resize images from any host that the `src` names, which costs the server bandwidth and compute. Report it when the default optimizer serves the pattern (not `unoptimized` or a custom `loader`) and a request can supply the `src`, for example a user-supplied image URL; a remote host that the app uses by name is not a finding by itself. Next.js 16 blocks local-network addresses unless `dangerouslyAllowLocalIP` is set (default `false`), so a wildcard hostname alone does not show that the server can reach a private network; report that only where the version or configuration turns that protection off. `images.domains` is deprecated and does not support wildcard matching, so it does not widen in this way.

**Bad** — `next=https://evil.example` sends the user to another site:

```js
import { NextResponse } from 'next/server'

export function GET(request) {
  const next = request.nextUrl.searchParams.get('next') ?? '/'
  return NextResponse.redirect(new URL(next, request.url))
}
```

**Good** — the value is parsed against the request URL, and the redirect goes there only when its origin is the request's own origin; anything else, including a value that does not parse, goes to `/`:

```js
import { NextResponse } from 'next/server'

export function GET(request) {
  const next = request.nextUrl.searchParams.get('next') ?? '/'
  let target
  try {
    target = new URL(next, request.url)
  } catch {
    target = null
  }
  const local = target?.origin === request.nextUrl.origin
  return NextResponse.redirect(local ? target : new URL('/', request.url))
}
```

## Conventions, not defects

- The App Router versus the Pages Router, Server Actions versus Route Handlers for a form, folder layout and route groups follow the repository's conventions.
- Choosing `loading.tsx`, Suspense boundaries or Partial Prerendering is a performance choice; it is a finding only with a measured or concrete effect.

## Sources

- Data security and Server Actions: https://nextjs.org/docs/app/guides/data-security, https://nextjs.org/docs/app/getting-started/updating-data
- Authentication and where to check access: https://nextjs.org/docs/app/guides/authentication
- Middleware, renamed proxy in Next.js 16: https://nextjs.org/docs/app/api-reference/file-conventions/proxy, https://nextjs.org/docs/app/guides/upgrading/version-16; CVE-2025-29927: https://github.com/vercel/next.js/security/advisories/GHSA-f82v-jwr5-mffw
- Server and Client Components and `server-only`: https://nextjs.org/docs/app/getting-started/server-and-client-components
- Environment variables: https://nextjs.org/docs/app/guides/environment-variables
- Caching and revalidation: https://nextjs.org/docs/app/guides/caching, https://nextjs.org/docs/app/getting-started/caching-and-revalidating; Next.js 15 changes: https://nextjs.org/docs/app/guides/upgrading/version-15
- `redirect` and `NextResponse`: https://nextjs.org/docs/app/api-reference/functions/redirect, https://nextjs.org/docs/app/api-reference/functions/next-response; `URL` parsing: https://url.spec.whatwg.org/#concept-basic-url-parser; `URL` constructor: https://developer.mozilla.org/en-US/docs/Web/API/URL/URL
- Images (`remotePatterns`, `domains`, `dangerouslyAllowLocalIP`, version history): https://nextjs.org/docs/app/api-reference/components/image

## Precedents

- **Server Actions check the request origin**: Next.js accepts Server Actions only as `POST` requests and compares the `Origin` header with the host (`Host` or `X-Forwarded-Host`), rejecting a mismatch. Do not report missing CSRF tokens on a Server Action. **Exception:** origins listed in `serverActions.allowedOrigins`, Route Handlers and Pages Router API routes, which get no such check and need their own protection when they authenticate with cookies, state changes in `GET` handlers, and Next.js versions before 14, where Server Actions were experimental.
- **Server Component code stays on the server**: the code and imports of a Server Component, a file without `'use client'` that only server code imports, are not sent to the browser. Do not report a secret read inside a Server Component as exposed to the client. **Exception:** values passed as props to a Client Component or returned from a Server Action, which are serialized to the browser, values rendered into the HTML, `NEXT_PUBLIC_` variables, and modules without `server-only` that a Client Component also imports.
- **`fetch` is not cached by default from Next.js 15**: in Next.js 15 and later, `fetch` in Server Components and `GET` Route Handlers is not stored in the Data Cache unless the call or the route opts in. Do not report per-user data shared through the Data Cache for a plain `fetch` there. **Exception:** `cache: 'force-cache'`, `next: { revalidate }` with a positive value, `dynamic = 'force-static'`, `unstable_cache` or `'use cache'` whose key or arguments leave out the user, Next.js 14 and earlier, where `fetch` in Server Components was cached by default, and a page prerendered at build time because it reads no request data.
