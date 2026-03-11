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
