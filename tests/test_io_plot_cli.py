import pandas as pd
import pytest

from materiality import load, load_classic_matrix, load_example, score, score_classic
from materiality.cli import main
from materiality.io import example_path
from materiality.plot import plot_interactive, plot_matrix
from materiality.report import to_markdown
from materiality.schema import ValidationError
from materiality.text import guess_pillar


def test_example_loads_and_is_labelled_fictional():
    d = load_example()
    assert len(d.topics) == 19
    assert d.survey["respondent_id"].nunique() == 41
    about = pd.read_excel(example_path(), sheet_name="about")
    assert "FICTIONAL" in about.iloc[0, 0]


def test_csv_dir_matches_excel():
    xl = score(load_example())
    csv = score(load(example_path().parent / "csv"))
    pd.testing.assert_series_equal(
        xl.set_index("topic_id")["impact_score"].sort_index(),
        csv.set_index("topic_id")["impact_score"].sort_index(),
    )


def test_load_rejects_unknown_type(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("{}")
    with pytest.raises(ValidationError):
        load(p)


def test_excel_without_topics_sheet(tmp_path):
    p = tmp_path / "bad.xlsx"
    pd.DataFrame({"a": [1]}).to_excel(p, sheet_name="other", index=False)
    with pytest.raises(ValidationError, match="topics"):
        load(p)


def test_classic_matrix_with_title_rows(tmp_path):
    # template-style sheet: title row, blank row, header, rows, some unscored
    p = tmp_path / "classic.xlsx"
    rows = [
        ["Materiality Assessment", None, None, None],
        [None, None, None, None],
        ["ESG Issue", "Stakeholder Importance (1-10)", "Business Impact (1-10)", "Priority"],
        ["Climate Change", 9, 8, None],
        ["Data Privacy", 6, 7, None],
        ["Diversity", None, None, None],
    ]
    pd.DataFrame(rows).to_excel(p, header=False, index=False)
    c = load_classic_matrix(p)
    assert list(c["topic"]) == ["Climate Change", "Data Privacy"]
    assert c["scale_max"].iloc[0] == 10
    s = score_classic(c)
    assert s.loc[0, "topic"] == "Climate Change"
    assert s.loc[0, "impact_score"] == pytest.approx(1 + 8 * 4 / 9)
    assert s.attrs["method"] == "classic"


def test_classic_out_of_range(tmp_path):
    p = tmp_path / "c.csv"
    pd.DataFrame({"Issue": ["x"], "Stakeholder (1-10)": [12], "Business (1-10)": [3]}).to_csv(p, index=False)
    with pytest.raises(ValidationError):
        load_classic_matrix(p)


def test_guess_pillar():
    assert guess_pillar("Climate Change") == "E"
    assert guess_pillar("Anti-corruption and bribery") == "G"
    assert guess_pillar("Labor Standards") == "S"
    assert guess_pillar("Something else", default="G") == "G"


def test_static_plot(tmp_path):
    s = score(load_example())
    out = tmp_path / "m.png"
    fig = plot_matrix(s, out)
    assert out.stat().st_size > 20_000
    assert len(fig.axes[0].texts) >= len(s)


def test_interactive_plot(tmp_path):
    pytest.importorskip("plotly")
    s = score(load_example())
    out = tmp_path / "m.html"
    fig = plot_interactive(s, out)
    assert out.exists() and "plotly" in out.read_text()[:5000].lower()
    assert sum(len(t.x) for t in fig.data) == len(s)


def test_markdown_report():
    md = to_markdown(score(load_example()), "T")
    assert md.startswith("# T") and "| 1 |" in md


def test_cli_build_all_outputs(tmp_path, capsys):
    rc = main([
        "build", str(example_path()), "--out", str(tmp_path / "m.png"), "--csv", str(tmp_path / "s.csv"),
        "--markdown", str(tmp_path / "s.md"), "--weight", "NGOs=2", "--impact-threshold", "2.5",
    ])
    assert rc == 0
    scores = pd.read_csv(tmp_path / "s.csv")
    assert len(scores) == 19 and {"impact_score", "financial_score", "quadrant"} <= set(scores.columns)


def test_cli_validate_and_errors(tmp_path, capsys):
    assert main(["validate", str(example_path())]) == 0
    assert "OK: 19 topics" in capsys.readouterr().out
    bad = tmp_path / "topics.csv"
    pd.DataFrame({"topic_id": ["a"], "topic": ["x"]}).to_csv(bad, index=False)
    assert main(["validate", str(bad)]) == 2


def test_cli_example_and_template(tmp_path):
    assert main(["example", str(tmp_path / "e.xlsx")]) == 0
    assert main(["template", str(tmp_path / "t.xlsx")]) == 0
    assert set(pd.ExcelFile(tmp_path / "t.xlsx").sheet_names) == {"topics", "survey", "weights"}


def test_cli_prints_markdown_without_outputs(capsys):
    assert main(["build", str(example_path())]) == 0
    assert "| # | Topic" in capsys.readouterr().out
