# Changelog

## 0.3.1

- Fix day-over-day cost change showing NaN when yesterday has zero or missing cost.
- Compare against the actual local-calendar yesterday rather than the previous active day.

## 0.3.0

- Recover aggregates when the local sessions database is replaced or truncated.
- Safely open SQLite paths with URI-reserved characters and avoid empty-ID response-body matches.
- Copy the active price seed to writable user storage on first edit; validate and atomically save settings without mutating the app bundle.
- Use lightweight status summaries while the dashboard is hidden, serialize extension polling, and surface source-health state.
- Preserve dashboard themes in the web frontend and expose meaningful polling health.

## 0.2.8

- Add six selectable, persistent themes across the dashboard and native sidebar accent.
- Add rolling usage summaries, month-end projections, estimated cache savings, model efficiency, and P50/P90 request analytics.
- Add a dedicated Insights navigation page.

## 0.2.7

- Initial VS Code-compatible desktop extension.
- Reuses the local SQLite usage pipeline and dashboard.
- Adds status bar cost, database selection, pricing configuration, CSV export, and six-language UI.
