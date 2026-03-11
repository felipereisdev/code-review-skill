# Nuxt.js — Code Review Checklist

- **SSR vs CSR**: `useFetch`/`useAsyncData` used for server-side data fetching; client-only logic wrapped in `<ClientOnly>` or `onMounted`
- **Hydration mismatches**: no logic that produces different output on server vs client outside of client-only wrappers
- **Auto-imports**: components and composables use Nuxt auto-imports correctly; no manual imports that conflict
- **Route meta**: page-level meta (auth guards, layouts) defined via `definePageMeta`, not in middleware ad hoc
- **State**: `useState` used for SSR-safe shared state; Pinia for complex global state
