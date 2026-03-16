"""Tests unitaires pour normalize_list — frontière LLM→DB."""
import pytest
from app.services.llm.llm_service import normalize_list


# ── cas normaux ────────────────────────────────────────────────────────────────

def test_normalize_list_from_clean_list():
    assert normalize_list(["Python", "SQL"]) == ["Python", "SQL"]


def test_normalize_list_filters_empty_strings():
    assert normalize_list(["Python", "", "  ", "SQL"]) == ["Python", "SQL"]


def test_normalize_list_none_input():
    assert normalize_list(None) is None


def test_normalize_list_empty_list():
    assert normalize_list([]) is None


# ── cas dégénérés issus du LLM ────────────────────────────────────────────────

def test_normalize_list_from_comma_string():
    """Le LLM retourne une chaîne au lieu d'une liste."""
    assert normalize_list("Python, SQL, Machine Learning") == [
        "Python", "SQL", "Machine Learning"
    ]


def test_normalize_list_from_single_string():
    """Le LLM retourne un seul élément en chaîne."""
    assert normalize_list("Python") == ["Python"]


def test_normalize_list_from_empty_string():
    assert normalize_list("") is None
    assert normalize_list("   ") is None


def test_normalize_list_non_string_elements():
    """Le LLM insère des entiers ou booléens dans la liste."""
    result = normalize_list([1, True, "Python"])
    assert result == ["1", "True", "Python"]


def test_normalize_list_from_dict_returns_none():
    """Le LLM retourne un dict au lieu d'une liste — on jette."""
    assert normalize_list({"key": "value"}) is None


def test_normalize_list_from_int_returns_none():
    assert normalize_list(42) is None


def test_normalize_list_strips_whitespace():
    assert normalize_list(["  Python  ", " SQL "]) == ["Python", "SQL"]
