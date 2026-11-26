# Changelog

## 0.4.4

- Rework the usage, composition and cache charts for small samples, empty periods and keyboard inspection. The model cost ranking includes every model and supports opening its requests.
- Preserve sub-cent costs across snapshots, reports and charts. Manual refresh rereads edited records, and background polling detects changes to the last processed row.
- Recover when the editor worker exits or the selected data source changes. Keep expanded replies visible across polls and show a retryable error when a reply cannot be loaded.
- Export all four CSV tables from the web dashboard and include cache-write tokens in the session and model exports.

## 0.4.3

- Redesign the dashboard in the International Typographic Style with an opaque navigation rail, ruled chart grid, tabular numerals and rectangular controls across all nine themes.
- Apply the selected palette to model charts and the activity heatmap.
- Introduce a vermilion extension icon with a three-stroke D, also used in the dashboard.

## 0.4.2

- Give navigation, the floating toolbar and session details a glass surface that follows the selected palette. Charts and totals retain solid backgrounds.
- Update the chart period selector with a sliding selection indicator. The date and language filters now support keyboard activation, and closing a session restores focus.
- Use opaque materials for reduced transparency and high contrast, and respect reduced motion during control transitions.

## 0.4.1

- Align paired overview charts on wide screens, including titles that wrap and model lists of different lengths.
- Add three solid dashboard themes: Porcelain, Apricot, and Plum.

## 0.4.0

- Explore complete local usage by date and model, with daily trends, cache breakdowns and cost rankings.
- Search and paginate recent requests, sort by cost, tokens or duration, and inspect cache writes and timing alongside the reply.
- Choose the metric displayed in the IDE status bar.
- Refresh the shared dashboard with solid theme palettes, adaptive navigation and reduced-motion support.

## 0.3.5

- Resolve the default sessions.db location per platform: `%APPDATA%\Devin\cli\sessions.db` on Windows, `~/.local/share/devin/cli/sessions.db` on POSIX, with the XDG path kept as a fallback for junction-based setups.
- Make the test suite pass on Windows: drop the `?` from test database filenames (illegal on win32) and close read-only connections explicitly so temp cleanup can unlink the files.
- Document the platform-specific default database locations.

## 0.3.4

- Add a complete Russian dashboard locale, Russian weekday labels, and Russian native-shell labels.
- Allow the Russian language preference to be saved and restored.

## 0.3.3

- Force Python worker standard streams to UTF-8 so non-ASCII session titles display correctly on Windows.
- Add current GPT-6.2, Claude 5.2/5.5, and Gemini 4 model rates to the bundled price table.

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
