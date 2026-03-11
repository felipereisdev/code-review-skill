# React — Code Review Checklist

- **Hooks rules**: hooks called at top level only; no hooks inside conditions or loops
- **useEffect dependencies**: dependency arrays are correct and complete; no missing deps
- **Memoization**: `useMemo` and `useCallback` used only when there's a measurable benefit
- **Key prop**: lists use unique, stable keys — never use array index as key
- **Component composition**: prefer composition over prop drilling; use context sparingly
- **State colocation**: state lives as close as possible to where it's used
- **Controlled components**: form inputs are controlled when the component needs their value
- **Error boundaries**: critical UI sections wrapped with error boundaries
- **Cleanup effects**: subscriptions and timers cleaned up in useEffect return function
- **Avoid inline definitions**: functions and objects not recreated on every render unnecessarily
- **Server vs Client components** *(Next.js only)*: proper separation of server and client components; no client-only APIs used in server components
