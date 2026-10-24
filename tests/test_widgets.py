from money_flow.gui.widgets import filter_options, resolve_option

VALUES = ["Aldi", "Amazon", "Amazon Fresh", "Dine out", "Tesco", "Esselunga", "M&S"]


def test_empty_query_returns_everything_in_order():
    assert filter_options(VALUES, "  ") == VALUES


def test_prefix_matches_come_before_substring_matches():
    # "es": Esselunga starts with it; Tesco and Amazon Fresh only contain it
    assert filter_options(VALUES, "es") == ["Esselunga", "Amazon Fresh", "Tesco"]


def test_filter_is_case_insensitive():
    assert filter_options(VALUES, "AMA") == ["Amazon", "Amazon Fresh"]
    assert filter_options(VALUES, "m&s") == ["M&S"]


def test_no_match():
    assert filter_options(VALUES, "xyz") == []


def test_resolve_option_fixes_case_and_whitespace():
    assert resolve_option(VALUES, "  tesco ") == "Tesco"
    assert resolve_option(VALUES, "tes") is None
    assert resolve_option(VALUES, "") is None

