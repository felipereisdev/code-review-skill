# Inertia.js — Code Review Checklist

> Load when project uses Inertia.js (check `package.json` for `@inertiajs/vue3` or `@inertiajs/react`).
> Detect Inertia version — v1 and v2 have different APIs (deferred props, `<Form>` component, `usePoll`, `WhenVisible` are v2+).

## Navigation

- **`<Link>` over `<a>`**: all internal navigation uses Inertia `<Link>`; `<a>` breaks SPA behavior and causes full page reload
- **Method on `<Link>`**: non-GET navigations use `method="post"` + `as="button"`; not a plain anchor
- **Prefetching**: `prefetch` added on `<Link>` for critical navigation paths
- **Programmatic navigation**: `router.visit()` used; `window.location` bypasses Inertia lifecycle
- **Preserve state**: `preserveState: true` passed to `router.visit()` when scroll position or form state must survive navigation

## Page Components

- **Single root element**: Vue page components have exactly one root element; Inertia mounts to the first root
- **Props typed**: `defineProps()` types match the data shape returned by the controller
- **No direct API calls**: data flows via Inertia props from the server; no `fetch()` / `axios` calls in page components unless absolutely necessary and documented

## Forms

- **`<Form>` vs `useForm` consistency**: one approach used consistently (Consistency Check applies); `<Form>` for simple cases, `useForm` for programmatic control
- **Submit prevention**: native `<form>` uses `@submit.prevent`
- **Loading state**: `processing` shown during submission; submit button disabled while processing
- **Error display**: per-field errors shown via `errors.field`; `hasErrors` used for global error banner
- **Reset on success**: `reset-on-success` / `setDefaultsOnSuccess` on `<Form>` where appropriate
- **Password reset**: `form.reset('password')` on success for password fields

## Deferred Props (v2+)

- **Loading skeleton**: every deferred prop has a visible loading state — skeleton, spinner, or placeholder; no blank UI while loading
- **`undefined` guard**: deferred prop checked before accessing sub-properties (`prop?.value`, not `prop.value`)
- **Fallback matches layout**: skeleton dimensions approximate the final content to prevent layout shift

## Polling (v2+)

- **`usePoll` over `setInterval`**: `usePoll` handles unmount cleanup and tab-inactive throttling; manual `setInterval` does not
- **Partial reloads**: `only: ['propName']` passed to avoid reloading unused props on every poll tick
- **`keepAlive`**: `keepAlive: true` set intentionally only when background-tab polling is required; default false preserved
- **`autoStart: false`**: manual polling wired to UI controls via returned `start()` / `stop()`

## Infinite Scroll / WhenVisible (v2+)

- **`<WhenVisible>` over scroll listeners**: used for infinite pagination; `data` and `params` set correctly
- **Fallback slot**: `<template #fallback>` has a loading indicator; not empty
- **Next page guard**: `WhenVisible` rendered only when `next_page_url` (or equivalent) is non-null

## Server-Side Patterns

- **`Inertia::render()`**: controller returns `Inertia::render('Page/Name', [...props])` — not a JSON response
- **Shared data**: global props (auth user, flash messages) shared via `Inertia::share()` in middleware, not duplicated per controller
- **Deferred props**: `Inertia::defer(fn)` used for props that are expensive to compute and not needed for first paint
- **Lazy props**: `Inertia::lazy(fn)` (v1) / `Inertia::defer(fn)` (v2) used appropriately per installed version

## Common Pitfalls

- `<a href>` instead of `<Link>` — full page reload, breaks SPA
- No loading state on deferred props — blank or broken UI during load
- Deferred prop accessed without `undefined` guard — runtime error before data arrives
- `window.location` for navigation — bypasses Inertia lifecycle, no progress bar
- `setInterval` instead of `usePoll` — no cleanup on unmount
- `<Form>` component used in projects with Inertia v1 — component does not exist in v1
- `fetch()` / `axios` calls in page components — bypasses Inertia's request lifecycle, breaks shared middleware logic
- Missing `preserveState` on visit when scroll position matters
