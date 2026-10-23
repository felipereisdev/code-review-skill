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

## Precedents

- **JSX escapes text**: React escapes every string rendered as a JSX child or as an ordinary, non-executable attribute value such as `className`, `title` or `alt`. Do not report XSS for user data rendered that way. **Exception:** `dangerouslySetInnerHTML`, direct DOM writes through refs (`ref.current.innerHTML = ...`), user-controlled URLs in `href`, `src`, `action` or `formAction`, where escaping does not stop a `javascript:` URL, user data in an `iframe` `srcDoc`, which the frame parses as a full HTML document, user data inside inline `<script>` content, and user-controlled objects spread as props (`{...props}`), which can set any of these.
- **State updates are batched**: since React 18 with `createRoot`, updates of the same priority queued synchronously in one event handler, timeout or promise callback are processed together instead of rendering once per setter (React may still restart or repeat a render, so no exact render count is guaranteed). Do not report consecutive `setState` calls in one synchronous callback as each forcing its own re-render. **Exception:** apps mounted with the legacy `ReactDOM.render` or running React 17 or lower, where updates outside React event handlers are not batched, updates wrapped in `flushSync`, updates of different priority, such as an urgent setter followed by one inside `startTransition` or `useTransition`, which can render separately, updates separated by an `await` or split across callbacks, and a traced effect or request that fires on an intermediate combination of those state values, which stays reportable.
- **StrictMode double runs are development-only**: `<StrictMode>` renders components twice and runs an extra effect setup-and-cleanup cycle in development, never in production builds. Do not report a doubled effect, request or log seen only in development as a production bug. **Exception:** a second run that exposes a missing cleanup (a subscription, listener or timer the effect never removes), which also leaks in production every time the component remounts.
