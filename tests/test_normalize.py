import re

from papa.normalize import TOKEN, normalize


def test_numbers_dates_urls_identifiers_become_token():
    text = "We shipped 3 features on 2026-06-27, see https://x.io/v2 and snake_case_id."
    out = normalize(text)
    assert not re.search(r"\d", out)
    assert "https" not in out
    assert "snake_case_id" not in out
    assert TOKEN in out


def test_plain_prose_is_unchanged():
    text = "The quiet river moved through the valley at dusk."
    assert normalize(text) == text


def test_percentages_and_decimals():
    out = normalize("Latency dropped 12.5% after the change.")
    assert "12.5" not in out and "%" not in out


def test_camel_and_snake_case():
    out = normalize("Call getUserName then read the config_value.")
    assert "getUserName" not in out
    assert "config_value" not in out


def test_sentence_terminating_period_survives_a_number():
    # the digit token must not swallow the period that ends the sentence
    out = normalize("I have 3. You have four.")
    assert out.count(".") == 2
