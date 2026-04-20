# Vue.js — Code Review Checklist

> Check sibling components for existing patterns before flagging any violation (see Consistency Check step).

## Reactivity & Composition

- **Composition API**: prefer `<script setup>` for new components
- **Reactivity**: `ref()` and `reactive()` used correctly; no reactivity lost by destructuring without `toRefs()`
- **`toRefs()`**: used when destructuring reactive objects to preserve reactivity
- **`shallowRef` / `shallowReactive`**: used for large objects where deep reactivity is unnecessary and costly
- **`markRaw()`**: used for objects that should never be made reactive (external class instances, third-party libs)
- **`watchEffect` vs `watch`**: `watchEffect` for effects depending on reactive state automatically; `watch` when source and callback must be explicit
- **`defineModel()`**: used (Vue 3.4+) for two-way binding instead of manual prop + emit pattern

## Template & Components

- **Props validation**: props have defined types and required/default values
- **Emit declarations**: events declared with `defineEmits` and typed
- **Component size**: components small and focused; large ones split into sub-components; SFC under 300 total lines, `<template>` and `<script>` each under 150
- **Computed vs methods**: derived state uses `computed`, not methods called in template
- **`v-for` keys**: unique stable keys — never array index as key
- **`v-memo`**: used on expensive list items to skip re-renders when dependencies unchanged
- **Template refs**: typed via `useTemplateRef()` or `ref<HTMLElement | null>(null)`
- **`defineExpose`**: only minimum necessary API exposed; not used to expose implementation details
- **`<Suspense>`**: used with explicit fallback when wrapping async components

## Composables

- **Naming**: composables prefixed with `use`, single focused responsibility
- **Cleanup**: cleanup logic (`onUnmounted`, event listener removal) inside the composable, not delegated to consumer
- **Conditional calls**: composables not called conditionally (same rule as React hooks)

## State & Communication

- **State management**: global state uses Pinia; component-local state stays local
- **`provide / inject`**: typed via `InjectionKey<T>`, not plain string keys; reserved for component-tree context, not as Pinia substitute
- **Lifecycle cleanup**: intervals, listeners, and subscriptions cleaned up on `onUnmounted`
- **Async components**: heavy components use `defineAsyncComponent` for code splitting

## Styles & Error Handling

- **Scoped styles**: styles use `scoped` or CSS Modules to prevent leaking across components
- **Dynamic classes**: `:class` used with object or array — not string concatenation
- **Error capturing**: `onErrorCaptured` implemented in components wrapping critical UI sections
- **Watchers**: excessive watchers avoided; computed properties preferred

## Common Pitfalls

- Destructuring reactive object without `toRefs()` — loses reactivity silently
- Array index as `v-for` key — causes incorrect diffing on reorder/delete
- Methods called in template for derived state instead of `computed` — recalculates every render
- Global state in composable module-level variable instead of Pinia — shared across instances
- `provide/inject` with plain string keys — no type safety, collision risk
- `watch` on deeply nested reactive object without `{ deep: true }` — misses nested changes
- Intervals or DOM listeners in `onMounted` without cleanup in `onUnmounted` — memory leak

---

## Inertia.js — Code Review Checklist

> Load this section when project uses Inertia.js (check `package.json` for `@inertiajs/vue3`).

### Navigation

- **`<Link>` over `<a>`**: all internal navigation uses Inertia's `<Link>` component; `<a>` breaks SPA behavior and causes full page reload
- **Method on `<Link>`**: non-GET navigations (logout, delete) use `method="post"` + `as="button"` on `<Link>`, not a plain `<a>`
- **Prefetching**: `prefetch` attribute added to `<Link>` on critical navigation paths to improve perceived performance
- **Programmatic navigation**: `router.visit()` used instead of `window.location`; options (`onSuccess`, `onError`, `preserveState`) passed where needed

### Forms

- **`<Form>` component vs `useForm`**: one approach used consistently across the project (Consistency Check applies); `<Form>` preferred for simple cases, `useForm` for programmatic control
- **Submit prevention**: native `<form>` elements use `@submit.prevent`; not relying on `<Form>` component without checking if it's available in the installed version
- **Loading state**: `processing` state shown during submission; button disabled while processing to prevent double-submit
- **Error display**: `errors.field` checked and displayed per field; `hasErrors` used for global error banners
- **Reset on success**: `reset-on-success` or `setDefaultsOnSuccess` used where form should clear after successful submit
- **`useForm` password reset**: `form.reset('password')` called in `onSuccess` when password field must clear on success without resetting other fields

### Deferred Props

- **Loading skeleton**: deferred props always have a loading state — `v-if="!prop"` with skeleton/spinner fallback; no blank or broken UI while data loads
- **`undefined` guard**: deferred prop checked for `undefined` before accessing sub-properties (e.g., `prop?.value`, not `prop.value`)

### Polling & Live Data

- **`usePoll`**: used over manual `setInterval` + `router.reload()`; handles cleanup on unmount and tab-inactive throttling automatically
- **`keepAlive` opt-in**: `keepAlive: true` set intentionally only when polling must continue in background tabs; default `false` preserved otherwise
- **`autoStart: false`**: used when polling should be triggered manually; returned `start()`/`stop()` wired to UI controls
- **Partial reloads**: `only: ['prop']` passed to `usePoll` to avoid reloading props not needed by the polling interval

### Infinite Scroll

- **`<WhenVisible>`**: used over manual scroll listeners for infinite pagination; `data` and `params` set correctly with the next page
- **Fallback slot**: `<template #fallback>` provided with a loading indicator

### Common Pitfalls (Inertia)

- `<a href>` instead of `<Link>` — full page reload, breaks SPA
- No loading state on form submission — double-submit possible
- Deferred prop accessed without `undefined` guard — runtime error before data loads
- `window.location` used for navigation — bypasses Inertia lifecycle
- `setInterval` used instead of `usePoll` — no cleanup on unmount, memory leak
- `<Form>` component used without verifying it's available in installed Inertia version
