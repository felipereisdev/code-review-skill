# Tailwind CSS — Code Review Checklist

> Detect Tailwind version from `package.json`. v3 and v4 have different import syntax and config conventions.

## Version-Specific Imports

| Version | Import syntax |
|---------|--------------|
| **v3** | `@tailwind base; @tailwind components; @tailwind utilities;` in CSS |
| **v4** | `@import "tailwindcss";` in CSS; config via `@theme` in CSS — no `tailwind.config.js` by default |

Flag if wrong syntax is used for the detected version.

## Conflicts & Redundancy

- **Conflicting utilities**: no redundant or overriding classes on the same element (e.g., `p-4 px-2` where `px-2` silently wins; `text-sm text-lg` where only the last wins)
- **Arbitrary values**: `[...]` used only when no equivalent utility exists in the configured scale; not used to bypass the design system
- **Design system tokens**: project color, spacing, and typography tokens used (e.g., `text-primary`, `bg-surface`) instead of hardcoded Tailwind palette values (e.g., `text-blue-500`) where a token exists

## Class Order & Readability

- **Consistent class order**: layout → sizing → spacing → typography → color → border → effects → transitions → responsive → state variants — consistent order improves readability and diff quality
- **Responsive prefixes ascending**: breakpoint variants in ascending order (`sm:` → `md:` → `lg:` → `xl:` → `2xl:`)

## Dark Mode

- **`dark:` variants present**: new UI elements have `dark:` variants when the rest of the project supports dark mode; not selectively omitted on new components

## Spacing

- **`gap-*` over margins between siblings**: `gap-*` on flex/grid parent used for spacing; `mt-*` / `mb-*` not used between siblings when a parent with `gap` would suffice

## Dynamic Classes

- **No string concatenation**: class names not constructed via template literals (e.g., `` `text-${color}-500` ``); full class names used so Tailwind's content scanner detects them
- **Safelist for dynamic classes**: if dynamic class generation is truly necessary, full class names added to `safelist` in config

## Componentization

- **`@apply` used sparingly**: only in base styles or reusable component layers; not as a workaround for long class strings in templates
- **Repeated patterns extracted**: identical long class strings repeated across multiple elements extracted into a component or Tailwind component class

## Verification Checklist

1. Visual rendering checked in browser
2. Responsive breakpoints tested
3. Dark mode verified if project uses it

## Common Pitfalls

- `p-4 px-2` — shorthand overridden silently; use `px-2 py-4` or just `p-4`
- `text-sm text-lg` — last class wins; pick one
- Arbitrary value `[#3b82f6]` instead of `text-blue-500` — bypasses design system, breaks theming
- `` `text-${color}-500` `` — not detected by Tailwind scanner, purged in production
- `mt-4` between siblings in a flex parent — use `gap-4` on the parent instead
- Dark mode missing on new component — inconsistent theming
- v4 project using `@tailwind base` directives — wrong syntax for v4
- v3 project using `@import "tailwindcss"` — wrong syntax for v3

## Precedents

- **Only used utilities are generated**: Tailwind generates CSS only for class names it finds in the scanned source files. Do not report added utility classes as growing the CSS bundle with unused rules. **Exception:** broad `safelist` patterns (v3) or other safelisting configuration, which generate every listed class whether it is used or not.
- **Class order in the attribute does not decide conflicts**: when two utilities on one element set the same property, the one that comes later in the generated stylesheet wins, not the one that comes later in the `class` attribute. Do not report reordering classes as a style change. **Exception:** class strings merged with `tailwind-merge` (`twMerge`, often wrapped as `cn()`), where the later class does win, and conflicting utilities on one element (`p-2 p-4`), which are a bug in themselves.
