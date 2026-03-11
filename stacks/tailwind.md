# Tailwind CSS — Code Review Checklist

- **Conflicting utilities**: no redundant or overriding classes in the same element (e.g. `p-4 px-2` where `px-2` silently overrides `p-4`; `text-sm text-lg` where only the last wins)
- **Arbitrary values**: `[...]` arbitrary values used only when no equivalent utility exists in the configured scale; not used to bypass the design system
- **Design system tokens**: project color, spacing, and typography tokens used (e.g. `text-primary`, `bg-surface`) instead of hardcoded Tailwind palette values (e.g. `text-blue-500`, `bg-gray-100`) where a token exists
- **Class order**: classes grouped and ordered consistently — layout → sizing → spacing → typography → color → border → effects → transitions → responsive → state variants — to improve readability and diff quality
- **Responsive prefixes in order**: breakpoint variants written in ascending order (`sm:` → `md:` → `lg:` → `xl:` → `2xl:`) within the class list
- **Dark mode**: `dark:` variants present on new UI elements when the rest of the project supports dark mode; not selectively omitted
- **Spacing with gap**: `gap-*` used for spacing between list or flex/grid items; `mt-*`/`mb-*` not used between siblings when a parent with `gap` would suffice
- **Dynamic class safety**: class names not constructed via string concatenation or template literals (e.g. `` `text-${color}-500` ``); full class names used so Tailwind's content scanner can detect them; dynamic classes added to the `safelist` if generation is truly necessary
- **`@apply` usage**: `@apply` used sparingly and only in base styles or reusable component layers — not as a way to avoid componentization or to work around long class strings in templates
- **Repeated class patterns**: long identical class strings repeated across multiple elements extracted into a component or a Tailwind component class rather than duplicated
