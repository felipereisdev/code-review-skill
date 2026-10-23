# Angular — Code Review Checklist

- **Standalone components**: prefer standalone components over NgModule-based ones
- **OnPush change detection**: components use `ChangeDetectionStrategy.OnPush` where possible
- **Unsubscribe**: observables unsubscribed via `takeUntilDestroyed`, `AsyncPipe`, or `DestroyRef`
- **Lazy loading**: feature modules/routes lazy loaded to reduce initial bundle
- **Typed forms**: reactive forms use strictly typed `FormGroup` and `FormControl`
- **TrackBy**: `*ngFor` uses `trackBy` function for efficient DOM updates
- **Services & DI**: business logic lives in injectable services, not components
- **Smart vs Dumb components**: clear separation between container (smart) and presentational (dumb) components
- **RxJS operators**: no nested subscribes — use `switchMap`, `mergeMap`, etc.; operators chained correctly
- **Signals**: prefer Angular Signals for new reactive state where applicable

## Precedents

- **Templates escape text and sanitize HTML and URLs**: Angular escapes `{{ }}` text interpolation, sanitizes untrusted HTML in `[innerHTML]`, and sanitizes URL-context bindings such as `<a [href]>` and `<img [src]>`. Do not report XSS solely because user data reaches one of those protected contexts through Angular's built-in template handling. **Exception:** values passed through `DomSanitizer.bypassSecurityTrust*` methods, custom sanitizers that omit the required checks, direct DOM writes such as `ElementRef.nativeElement.innerHTML = ...`, and templates compiled from untrusted source; CSS style bindings are outside this guarantee because Angular does not filter their CSS values.
- **The `async` pipe unsubscribes**: an observable consumed with `| async` is unsubscribed when the component is destroyed. Do not report a missing unsubscribe for it. **Exception:** manual `.subscribe()` calls on long-lived observables in the same component.
- **`HttpClient` requests complete**: an `HttpClient` observable emits its response and completes. Do not report a missing unsubscribe on a plain `http.get(...).subscribe()` as a memory leak. **Exception:** requests chained to long-lived sources that never complete, such as `interval`, form `valueChanges`, `fromEvent` or router events.
