# Contributing

Thanks for helping! Bug reports, ideas and pull requests are all welcome.

## Setup

```bash
git clone https://github.com/DataWithSyed/materiality-matrix.git
cd materiality-matrix
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

## Guidelines

- **Cite real documents.** Any rule that claims to follow a standard (ESRS,
  GRI, ...) must cite the document and paragraph in `docs/METHOD.md`.
  Where the standard is silent, say that the rule is a choice of this tool.
- **No real company or personal data in examples.** Example data must be
  clearly labelled as fictional, or come from a public source with a citation
  and a licence that allows reuse.
- **Tests for every change.** New scoring rules need a hand-checked test.
- **Keep the core light.** Heavy dependencies go behind optional extras.
- Regenerate example outputs with:
  ```bash
  python examples/make_example_data.py
  materiality build src/materiality/data/example/example_assessment.xlsx \
      --out assets/example_matrix.png --html assets/example_matrix.html \
      --csv assets/example_scores.csv --markdown assets/example_summary.md \
      --title "Double materiality matrix - fictional example"
  ```

## Good first issues

Items in [ROADMAP.md](ROADMAP.md) marked as small (importers, plot themes,
extra validation checks) are a good start. Open an issue first for larger changes.
