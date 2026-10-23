# TypeScript — Code Review Checklist

## Type Safety
- **Strict mode**: no use of `any` unless truly unavoidable; prefer `unknown` for untyped data
- **Type safety**: function signatures fully typed; no implicit `any`
- **No type assertions**: avoid `as` casts; prefer type narrowing or generics
- **Null handling**: strict null checks respected; use optional chaining and nullish coalescing
- **catch clauses**: `catch (e)` typed as `unknown`, not `any`; narrowed before use
- **Promise types**: async functions explicitly typed as `Promise<T>`; not left to infer `Promise<any>`

## Advanced Types
- **Enums vs unions**: prefer string literal unions over enums when possible
- **Generics**: used where they add real type safety; not overused for unnecessary abstraction
- **Type narrowing**: proper use of type guards, discriminated unions, and `satisfies`
- **Utility types**: use `Partial`, `Pick`, `Omit`, `Record`, `Readonly`, `ReturnType`, etc. instead of redefining shapes
- **Interface vs Type**: consistent usage; interfaces for object shapes, types for unions/intersections
- **as const**: used for literal objects and arrays that should not be widened to `string[]` or `number`
- **Readonly**: `Readonly<T>` and `ReadonlyArray<T>` used for data that must not be mutated
- **Branded types**: domain primitives that must not be interchangeable use nominal/branded types (e.g. `UserId`, `Email`)
- **never for exhaustiveness**: `never` used in switch/if-else branches to guarantee all cases are handled at compile time
- **Template literal types**: used for typed dynamic keys (e.g. `${string}Id`, event names) where appropriate

## Runtime Validation
- **Runtime validation**: types at system boundaries (API responses, `localStorage`, env vars, form input) validated at runtime with Zod, Valibot, or similar — TypeScript types alone do not validate at runtime
- **Schema inference**: type inferred from the schema (`z.infer<typeof schema>`) rather than duplicating the definition manually

## Organisation
- **Centralized types**: domain types defined in dedicated type files; not scattered inline across components or functions
- **Barrel exports**: `index.ts` re-exports organized to avoid deep import paths, without creating circular dependencies

## Precedents

- **`import type` is erased**: `import type` and `export type` declarations are removed from the emitted JavaScript, so they never load the module at run time. Do not report them as adding a runtime dependency, a runtime import cycle or bundle size. **Exception:** imports without the `type` keyword, and inline `type` modifiers (`import { type X } from "mod"`) under `verbatimModuleSyntax`, which keep an `import {} from "mod"` that still loads the module.
- **Exhaustive switches are checked by the compiler**: a `switch` over a union whose `default` branch assigns the value to a `never` variable fails type-checking when a member of the union has no `case`. Do not report a missing `case` for a member of that union in a project where the type checker runs over that file. **Exception:** switches without the `never` assignment (or an equivalent `satisfies never` check); code that no type checker runs over, such as transpile-only builds (Vite, esbuild or Babel without a separate `tsc` step) or Node type stripping, which execute the switch unchecked; and values that can fall outside the union at run time, such as untyped input, `as` casts, `any` or a mutable alias with a wider type, where the `default` branch needs real handling.
