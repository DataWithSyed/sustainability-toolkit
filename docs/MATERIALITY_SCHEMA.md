# Input schema

Inputs are a workbook (`.xlsx`) with sheets named `topics`, and optionally
`survey` and `weights` (case-insensitive; other sheets are ignored), **or** a
folder with `topics.csv`, `survey.csv`, `weights.csv`. Column names are
case-insensitive and spaces become underscores (`Topic ID` -> `topic_id`).

Run `materiality validate FILE` to check a file; all problems are listed at once.

## `topics` (required)

| column | type | required | notes |
|---|---|---|---|
| `topic_id` | text | yes | unique |
| `topic` | text | yes | display name |
| `esrs` | text | yes | `E1`-`E5`, `S1`-`S4`, `G1`, or `ENTITY` for entity-specific topics |
| `pillar` | `E`/`S`/`G` | for `ENTITY` | derived from `esrs` otherwise |
| `subtopic` | text | no | e.g. an ESRS 1 AR 16 sub-topic |
| `impact_type` | text | no | `actual_negative` (default), `potential_negative`, `actual_positive`, `potential_positive` |
| `scale` | 1-5 | for impact | how grave / how beneficial |
| `scope` | 1-5 | for impact | how widespread |
| `irremediability` | 1-5 | negative impacts | how hard to remediate |
| `impact_likelihood` | 0-1 | potential impacts | |
| `human_rights` | yes/no | no | potential negative human-rights impact |
| `fin_magnitude` | 1-5 | for financial | potential magnitude of financial effects |
| `fin_likelihood` | 0-1 | with `fin_magnitude` | |
| `time_horizon` | `short`/`medium`/`long` | no | warning if other |
| `value_chain` | `upstream`/`own_operations`/`downstream` | no | warning if other |
| `description` | text | no | shown on hover in the HTML matrix |

A topic may leave the assessment columns empty if it has survey answers;
then the survey alone drives that axis.

## `survey` (optional, long format)

| column | type | notes |
|---|---|---|
| `respondent_id` | text | one respondent may answer many topics |
| `stakeholder_group` | text | e.g. Employees, Investors |
| `topic_id` | text | must exist in `topics` |
| `impact_rating` | 1..N | N = `--rating-scale` (default 5) |
| `financial_rating` | 1..N | at least one rating column is required |

Each respondent may rate each topic at most once.

## `weights` (optional)

| column | type | notes |
|---|---|---|
| `stakeholder_group` | text | every surveyed group needs a weight if this sheet exists |
| `weight` | number >= 0 | relative; 0 excludes a group |

Without a `weights` sheet every group has weight 1.

## Classic two-axis sheets

`materiality classic FILE` finds a header row containing an *issue/topic*
column, a *stakeholder* column and a *business/financial* column (title rows
above it are skipped) and reads the scale maximum from headers like `(1-10)`.
