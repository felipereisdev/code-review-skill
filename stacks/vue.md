# Vue.js — Code Review Checklist

## Reactivity & Composition
- **Composition API**: prefer Composition API (`<script setup>`) for new components
- **Reactivity**: use `ref()` and `reactive()` correctly; avoid losing reactivity by destructuring
- **toRefs**: use `toRefs()` when destructuring reactive objects to preserve reactivity
- **shallowRef / shallowReactive**: use `shallowRef` or `shallowReactive` for large objects where deep reactivity is unnecessary and costly
- **markRaw**: use `markRaw()` for objects that should never be made reactive (external class instances, maps, etc.)
- **watchEffect vs watch**: `watchEffect` used for effects that depend on reactive state automatically; `watch` used when the source and callback must be explicit
- **defineModel**: use `defineModel()` (Vue 3.4+) for two-way binding in child components instead of manual prop + emit pattern

## Template & Components
- **Props validation**: props have defined types and required/default values
- **Emit declarations**: events declared with `defineEmits` and properly typed
- **Component size**: components are small and focused; large ones split into sub-components
- **Computed vs methods**: derived state uses `computed`, not methods called in template
- **v-for keys**: lists use unique, stable keys — never use array index as key
- **v-memo**: used on expensive list items to skip re-renders when dependencies have not changed
- **Template refs**: typed correctly via `useTemplateRef()` or `ref<HTMLElement | null>(null)`
- **defineExpose**: only the minimum necessary API is exposed; not used to expose internal implementation details
- **Suspense**: `<Suspense>` used with an explicit fallback when wrapping async components

## Composables
- **Naming**: composables prefixed with `use` and have a single, focused responsibility
- **Cleanup**: cleanup logic (`onUnmounted`, event listener removal) is handled inside the composable, not delegated to the consumer
- **Conditional calls**: composables not called conditionally (same rule as React hooks)

## State & Communication
- **State management**: global state uses Pinia; component-local state stays local
- **provide / inject**: typed via `InjectionKey<T>`, not plain string keys; reserved for component-tree context, not as a substitute for Pinia
- **Lifecycle cleanup**: intervals, listeners, and subscriptions cleaned up on `onUnmounted`
- **Async components**: heavy components use `defineAsyncComponent` for code splitting

## Styles & Error Handling
- **Scoped styles**: styles use `scoped` attribute or CSS Modules to prevent leaking across components
- **Dynamic classes**: `:class` used with an object or array — not string concatenation
- **Error capturing**: `onErrorCaptured` implemented in components that wrap critical UI sections
- **Watchers**: avoid excessive watchers; prefer computed properties when possible
