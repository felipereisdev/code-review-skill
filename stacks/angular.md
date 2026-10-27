# Angular — Code Review Checklist

> Check sibling components and services for existing patterns before flagging a convention (see Consistency Check step). Report an item only with a concrete trigger → effect in the changed code. A problem that the Angular compiler with the repository's template settings, TypeScript or ESLint as configured in the repository already reports is not a finding. Read the Angular version from `@angular/core` in `package.json` or the lockfile. Change detection items depend on how the app schedules it: Angular v21 and later are zoneless by default, v20 apps opt in with `provideZonelessChangeDetection()`, and an app that loads `zone.js` with zone-based change detection is not zoneless.

## Security

- **Trust bypasses with untrusted values**: `DomSanitizer.bypassSecurityTrustHtml`, `bypassSecurityTrustUrl`, `bypassSecurityTrustResourceUrl`, `bypassSecurityTrustScript` and `bypassSecurityTrustStyle` turn off Angular's sanitization for the value they wrap. Passing a value that a user or another tenant controls, such as a comment body, a profile link or a CMS field, to one of them is XSS. **Not a finding:** a bypass of a constant or of a value that the code builds only from constants, and HTML that `sanitizer.sanitize(SecurityContext.HTML, value)` returned and nothing changed afterwards.
- **Direct DOM writes**: `nativeElement.innerHTML`, `outerHTML`, `insertAdjacentHTML` and `document.write` are browser APIs, not Angular templates, and do not sanitize; user data written through them is XSS unless the app enforces Trusted Types.
- **Route guards as access control**: a `canActivate`, `canMatch` or `canLoad` guard only decides whether the browser shows a route, and anyone can call the API behind it directly. Report data that the change protects only with a guard when the change adds or edits the API endpoint without a server-side check, or the endpoint is in the repository and does not check the user.

## Subscriptions and RxJS

- **Subscriptions that outlive the component**: a manual `.subscribe()` in a component or directive to an observable that does not complete, such as a service `Subject` or `BehaviorSubject`, a store selector, `valueChanges` of a form control owned by a longer-lived object, router events, `interval` or `fromEvent`, keeps running after the component is destroyed: its callback still runs, it keeps the component in memory, and every new instance adds another subscription. End it with `takeUntilDestroyed()` (Angular 16+, stable since 19), `DestroyRef.onDestroy`, `ngOnDestroy` or the `async` pipe, or read it with `toSignal`, which unsubscribes when its injection context is destroyed. **Not a finding:** observables that complete after their value, such as `HttpClient` requests (see Precedents), and subscriptions in root services, which live as long as the app.
- **`takeUntilDestroyed()` outside an injection context**: called without an argument, it injects the current `DestroyRef`, which is possible only in a constructor, a field initializer or a provider factory. Called in `ngOnInit` or another method, it throws `NG0203` when that code runs. Inject `DestroyRef` in a field and pass it: `takeUntilDestroyed(this.destroyRef)`.
- **Nested subscriptions on repeating streams**: subscribing again inside the callback of a stream that emits many times, such as a search box's `valueChanges`, starts one request per value, and a slow response to an older value can arrive last and overwrite the newer result. `switchMap` stops emitting values from the previous inner observable when a new one starts and unsubscribes from it, which aborts an in-progress `HttpClient` request. **Not a finding:** an outer observable that emits once, and `concatMap` or `mergeMap` where every request must complete.

**Bad** — a slow response for an old search term can arrive last and replace the newer results:

```ts
@Component({ selector: 'app-search', templateUrl: './search.html' })
export class SearchComponent {
  private readonly api = inject(ProductApi);
  readonly query = new FormControl('', { nonNullable: true });
  results: Product[] = [];

  constructor() {
    this.query.valueChanges.subscribe((term) => {
      this.api.search(term).subscribe((products) => {
        this.results = products;
      });
    });
  }
}
```

**Good** — `switchMap` drops the previous request; the template reads `results()`, and a failed search shows an empty list instead of ending the stream:

```ts
@Component({ selector: 'app-search', templateUrl: './search.html' })
export class SearchComponent {
  private readonly api = inject(ProductApi);
  readonly query = new FormControl('', { nonNullable: true });
  readonly results = toSignal(
    this.query.valueChanges.pipe(
      switchMap((term) => this.api.search(term).pipe(catchError(() => of([] as Product[])))),
    ),
    { initialValue: [] as Product[] },
  );
}
```

**Bad** — `ngOnInit` is not an injection context, so `takeUntilDestroyed()` throws `NG0203`:

```ts
@Component({ selector: 'app-price', template: '{{ price() }}' })
export class PriceComponent implements OnInit {
  readonly symbol = input.required<string>();
  readonly price = signal<number | null>(null);
  private readonly prices = inject(PriceService);

  ngOnInit() {
    this.prices
      .watch(this.symbol())
      .pipe(takeUntilDestroyed())
      .subscribe((price) => this.price.set(price));
  }
}
```

**Good** — the `DestroyRef` comes from a field initializer and is passed explicitly:

```ts
@Component({ selector: 'app-price', template: '{{ price() }}' })
export class PriceComponent implements OnInit {
  readonly symbol = input.required<string>();
  readonly price = signal<number | null>(null);
  private readonly prices = inject(PriceService);
  private readonly destroyRef = inject(DestroyRef);

  ngOnInit() {
    this.prices
      .watch(this.symbol())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((price) => this.price.set(price));
  }
}
```

## Change Detection

- **Mutated inputs of `OnPush` components**: Angular checks an `OnPush` component when one of its inputs receives a new value, comparing by identity. Mutating an object or array that is already bound (`this.items.push(item)`) keeps the same reference, so an `OnPush` child that renders it keeps showing the old data. Assign a new array or object, or hold the data in a signal. **Not a finding:** a child that uses the default strategy in an app with zone-based change detection, and data that the child reads through a signal or the `async` pipe.
- **Plain fields changed in callbacks**: in a zoneless app, and in `OnPush` components of any app, assigning a plain field in a `setTimeout`, promise, `subscribe` or third-party callback does not schedule a check of that view, so it keeps showing the old value until something else triggers one. Hold the value in a signal that the template reads, use the `async` pipe, or call `ChangeDetectorRef.markForCheck()`. **Not a finding:** components with the default strategy in an app with zone-based change detection, and template or host listener callbacks, which notify Angular themselves.
- **List tracking**: `@for (item of items; track $index)` ties each view to a position, so when items are inserted, removed or reordered, Angular reuses a view for a different item, and per-row component state, focus and unsaved input stay with the position instead of the item. Track a stable unique property (`track item.id`). **Not a finding:** `track $index` on a list that never changes after it is rendered.

**Bad** — the cart list uses `OnPush`, so after `push` it still shows the old items:

```ts
// <app-cart-list [items]="items" /> is OnPush
addItem(item: CartItem) {
  this.items.push(item);
}
```

**Good** — a new array reference makes Angular check the `OnPush` child:

```ts
// <app-cart-list [items]="items" /> is OnPush
addItem(item: CartItem) {
  this.items = [...this.items, item];
}
```

## Conventions, not defects

- Standalone components or NgModules, `OnPush` or the default strategy, signals or RxJS, typed reactive forms, and the split between container and presentational components follow the app's existing choices; none of them is a finding by itself.
- Business logic in services instead of components, and lazy-loaded routes, are design choices. A missing lazy route is a finding only with a concrete cost, such as a large dependency that the change adds to the initial bundle.

## Sources

- Security, sanitization, Trusted Types: https://angular.dev/best-practices/security; `DomSanitizer`: https://angular.dev/api/platform-browser/DomSanitizer
- Route guards and server-side authorization: https://angular.dev/guide/routing/route-guards
- `takeUntilDestroyed`: https://angular.dev/api/core/rxjs-interop/takeUntilDestroyed; `NG0203`: https://angular.dev/errors/NG0203; `toSignal`: https://angular.dev/api/core/rxjs-interop/toSignal; `DestroyRef` and `ngOnDestroy`: https://angular.dev/guide/components/lifecycle
- Aborting `HttpClient` requests: https://angular.dev/guide/http/making-requests; `switchMap`: https://rxjs.dev/api/operators/switchMap
- `OnPush`: https://angular.dev/best-practices/skipping-subtrees; zoneless change detection: https://angular.dev/guide/zoneless
- `@for` and `track`: https://angular.dev/guide/templates/control-flow

## Precedents

- **Templates escape text and sanitize HTML and URLs**: Angular escapes `{{ }}` text interpolation, sanitizes untrusted HTML in `[innerHTML]`, and sanitizes URL-context bindings such as `<a [href]>` and `<img [src]>`. Do not report XSS solely because user data reaches one of those protected contexts through Angular's built-in template handling. **Exception:** values passed through `DomSanitizer.bypassSecurityTrust*` methods, custom sanitizers that omit the required checks, direct DOM writes such as `ElementRef.nativeElement.innerHTML = ...`, and templates compiled from untrusted source; CSS style bindings are outside this guarantee because Angular does not filter their CSS values.
- **The `async` pipe unsubscribes**: an observable consumed with `| async` is unsubscribed when the component is destroyed. Do not report a missing unsubscribe for it. **Exception:** a manual `.subscribe()` on the same long-lived observable elsewhere in the component, which the pipe does not manage and which still needs an unsubscribe.
- **`HttpClient` requests complete**: an `HttpClient` observable emits its response and completes, unless a configured interceptor replaces that response with a stream that stays open. Do not report a missing unsubscribe on a plain `http.get(...).subscribe()` as a memory leak when no such interceptor is active. **Exception:** requests chained to long-lived sources that never complete, such as `interval`, form `valueChanges`, `fromEvent` or router events, and interceptors that replace the response with a stream that does not complete, such as one that concatenates `NEVER` or adds polling, retry or repeat logic that never ends.
