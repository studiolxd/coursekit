"""Inclusive language (`rules › inclusive_language`): the rule the agents get and the warnings of `coursekit verify`."""

import pytest

from coursekit import agents, lang
from coursekit import course as coursemod
from coursekit.verify import Report, check_inclusive


def warnings(lines: list[str], mode: str, language: str = "es", skip: tuple[str, ...] = ()) -> list[str]:
    report = Report()
    check_inclusive("content.md", lines, mode, lang.tokens(language), report, skip)
    assert not report.errors
    return report.warnings


def test_neutral_warns_once_per_generic_word_with_its_lines_and_alternative():
    found = warnings(["Los alumnos leen.", "Texto.", "Cada alumno escribe; los ALUMNOS repasan.", "Los niños juegan."], "neutral")
    assert len(found) == 3
    assert any("“alumnos” (lines 1, 3)" in w and "el alumnado" in w for w in found)
    assert any("“alumno” (lines 3)" in w for w in found)
    assert any("“los niños”" in w and "la infancia" in w for w in found)


def test_neutral_and_split_warn_about_slashes_and_at_signs_but_not_y_o():
    lines = ["El/la alumno/a lee y/o escribe.", "Bienvenid@s."]
    for mode in ("neutral", "split"):
        forms = [w for w in warnings(lines, mode) if "slash" in w]
        assert len(forms) == 3 and not any("y/o" in w for w in forms)
    assert not any("alumno”" in w for w in warnings(lines, "split"))  # split does not warn about generic words


def test_none_and_slash_warn_about_nothing():
    lines = ["Los alumnos leen.", "El/la alumno/a escribe."]
    assert warnings(lines, "none") == [] and warnings(lines, "slash") == []


def test_code_comments_addresses_and_format_headings_are_left_out():
    lines = ["```", "clientes = []", "```", "<!-- para los alumnos -->", "<!-- nota", "los alumnos", "-->",
             "Mira https://example.com/alumno/a o escribe a soporte@example.com.", "### Instrucciones para el alumno"]
    assert warnings(lines, "neutral", skip=("### Instrucciones para el alumno",)) == []


def test_english_lexicon():
    found = warnings(["He or she gives his/her name to the chairman."], "neutral", "en")
    assert len(found) == 3 and any("they" in w for w in found) and any("chair" in w for w in found)


def test_both_languages_have_a_lexicon():
    for code in ("es", "en"):
        lexicon = lang.tokens(code)["inclusive"]
        assert lexicon["generic"] and lexicon["marks"]


def test_the_rule_defaults_to_neutral_and_rejects_unknown_values():
    assert coursemod.inclusive_language({}) == "neutral"
    assert coursemod.inclusive_language({"inclusive_language": "Split"}) == "split"
    with pytest.raises(coursemod.RuleError):
        coursemod.inclusive_language({"inclusive_language": "x"})


def test_every_mode_has_a_rule_for_the_agents():
    assert set(agents.INCLUSIVE_RULES) == set(coursemod.INCLUSIVE_MODES)
