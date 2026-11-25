# `sustainkit.materiality`: method

This page explains exactly how `sustainkit.materiality` turns inputs into scores,
and which parts come from the standards versus which are choices made by this
tool. All scores use a 1-5 scale; likelihood-weighted scores can fall below 1.

## 1. Double materiality

Under ESRS a sustainability matter is material if it is material from the
**impact** perspective, the **financial** perspective, or both (ESRS 1,
chapter 3). This tool therefore flags a topic as `material` when **either**
score reaches its threshold, and puts it in one of four quadrants:
`double`, `impact`, `financial` or `not material`.

## 2. Impact materiality (inside-out)

Source: ESRS 1 section 3.4, paras 43-46, and AR 10-11 (Delegated Regulation (EU) 2023/2772).

| Impact type | Standard says | Score in this tool |
|---|---|---|
| actual negative | severity | `severity = mean(scale, scope, irremediability)` |
| potential negative | severity and likelihood | `severity x likelihood` |
| potential negative, human rights | severity takes precedence over likelihood (para 45) | `severity` (likelihood ignored)\* |
| actual positive | scale and scope (para 46a) | `mean(scale, scope)` |
| potential positive | scale, scope and likelihood (para 46b) | `mean(scale, scope) x likelihood` |

\* A conservative simplification; turn it off with
`ScoringConfig(human_rights_precedence=False)`.

AR 11 notes that *any* of the three severity characteristics can make a
negative impact severe. A plain mean can understate a very irremediable but
small-scale impact; a "max" or weighted rule is on the roadmap.

## 3. Financial materiality (outside-in)

Source: ESRS 1 section 3.5, paras 47-51. Para 51: materiality of risks and
opportunities is assessed on a combination of the likelihood of occurrence and
the potential magnitude of the financial effects.

`financial = fin_magnitude (1-5) x fin_likelihood (0-1)`

## 4. Stakeholder survey

ESRS 1 (section 3.1) and GRI 3 both treat engagement with affected
stakeholders as an input to identifying impacts. They do not prescribe a
survey formula. This tool:

1. rescales ratings to 1-5 if the survey used another scale (e.g. 1-10);
2. summarises each stakeholder group's ratings per topic (mean or median);
3. combines groups with explicit weights, renormalised over the groups that
   rated that topic, so a group counts by its **weight**, not its head-count;
4. blends the survey into the assessment:
   `score = (1 - b) x assessment + b x survey` (default `b = 0.3` per axis).
   If a topic has only an assessment or only a survey, that one is used.

`group_spread` (largest minus smallest group mean for impact) is reported as
a simple disagreement signal.

## 5. Thresholds and ranking

ESRS do not set numeric thresholds. The default 3.0 on both axes is the
midpoint of the 1-5 scale and is a placeholder: set your own and document
why. Topics are ranked by `priority = sqrt(impact^2 + financial^2)`, a common
convention for ordering matrix points, not a requirement of any standard.

## 6. Classic matrices

`materiality classic` reads the older "importance to stakeholders vs impact
on business" layout. That is **not** double materiality: the y-axis is
stakeholder concern, not the undertaking's impacts. It is supported so
existing sheets can be plotted and migrated.

## Sources

1. Commission Delegated Regulation (EU) 2023/2772, Annex I, ESRS 1 *General requirements*. https://eur-lex.europa.eu/eli/reg_del/2023/2772/oj
2. Directive (EU) 2022/2464 (CSRD). https://eur-lex.europa.eu/eli/dir/2022/2464/oj
3. EFRAG, *IG 1: Materiality Assessment Implementation Guidance* (2024).
4. Global Reporting Initiative, *GRI 3: Material Topics 2021*.
5. EFRAG Knowledge Hub, simplified ESRS 1 (version labelled 2026-09-21 Official Journal). https://knowledgehub.efrag.org/eng/interactive/simplified-esrs/esrs-1/2026-09-21-official-journal
