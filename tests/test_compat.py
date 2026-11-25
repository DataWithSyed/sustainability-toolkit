"""``import materiality`` (v0.1 API) still works after the move to sustainkit."""


def test_old_imports_still_work():
    import materiality
    import materiality.scoring as old_scoring
    from materiality.plot import plot_matrix  # noqa: F401

    import sustainkit
    from sustainkit.materiality import scoring

    assert old_scoring is scoring
    assert materiality.score is scoring.score
    assert materiality.__version__ == sustainkit.__version__


def test_old_example_still_scores():
    import materiality

    scored = materiality.score(materiality.load_example())
    assert len(scored) == 19
