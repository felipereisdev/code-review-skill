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
