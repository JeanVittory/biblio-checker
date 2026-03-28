from __future__ import annotations

import pytest

from biblio_checker_worker.langgraph.scoring import (
    author_similarity,
    compute_match_score,
    title_similarity,
)


# ---------------------------------------------------------------------------
# title_similarity
# ---------------------------------------------------------------------------

class TestTitleSimilarity:
    def test_identical_titles_return_1_0(self) -> None:
        assert title_similarity("Deep Learning", "Deep Learning") == pytest.approx(1.0)

    def test_case_insensitive(self) -> None:
        assert title_similarity("Deep Learning", "deep learning") == pytest.approx(1.0)

    def test_punctuation_insensitive(self) -> None:
        # Punctuation stripped before comparison
        assert title_similarity("Hello, World.", "Hello World") == pytest.approx(1.0)

    def test_none_title_a_returns_0(self) -> None:
        assert title_similarity(None, "Some Title") == pytest.approx(0.0)

    def test_none_title_b_returns_0(self) -> None:
        assert title_similarity("Some Title", None) == pytest.approx(0.0)

    def test_both_none_returns_0(self) -> None:
        assert title_similarity(None, None) == pytest.approx(0.0)

    def test_empty_string_returns_0(self) -> None:
        assert title_similarity("", "Something") == pytest.approx(0.0)
        assert title_similarity("Something", "") == pytest.approx(0.0)

    def test_completely_different_titles_return_low_score(self) -> None:
        score = title_similarity("Quantum Physics", "Renaissance Painting")
        assert score < 0.4

    def test_similar_but_not_identical_titles_return_moderate_score(self) -> None:
        score = title_similarity(
            "Deep Learning for Natural Language Processing",
            "Deep Learning for NLP",
        )
        assert 0.6 < score < 1.0

    def test_subtitle_variation_returns_moderate_score(self) -> None:
        score = title_similarity(
            "Machine Learning: A Survey",
            "Machine Learning",
        )
        # Should be moderate (0.7-0.9), not 1.0 but not too low
        assert 0.6 < score < 1.0

    def test_returns_float_in_0_1_range(self) -> None:
        score = title_similarity("Alpha", "Beta")
        assert 0.0 <= score <= 1.0

    def test_leading_trailing_whitespace_is_normalized(self) -> None:
        assert title_similarity("  Hello World  ", "Hello World") == pytest.approx(1.0)

    def test_multiple_internal_spaces_are_normalized(self) -> None:
        assert title_similarity("Hello   World", "Hello World") == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# author_similarity
# ---------------------------------------------------------------------------

class TestAuthorSimilarity:
    def test_empty_list_a_returns_0(self) -> None:
        assert author_similarity([], ["Smith, John"]) == pytest.approx(0.0)

    def test_empty_list_b_returns_0(self) -> None:
        assert author_similarity(["Smith, John"], []) == pytest.approx(0.0)

    def test_both_empty_returns_0(self) -> None:
        assert author_similarity([], []) == pytest.approx(0.0)

    def test_identical_single_author_returns_high_score(self) -> None:
        score = author_similarity(["John Smith"], ["John Smith"])
        assert score == pytest.approx(1.0)

    def test_same_first_author_different_rest_returns_high_score(self) -> None:
        score = author_similarity(
            ["Smith, John", "Doe, Jane", "Brown, Alice"],
            ["Smith, John", "Other, Author"],
        )
        # First-author matches exactly; score dominated by that
        assert score > 0.65

    def test_completely_different_authors_return_low_score(self) -> None:
        score = author_similarity(["Smith, John"], ["Zhang, Wei"])
        assert score < 0.4

    def test_case_insensitive(self) -> None:
        score = author_similarity(["john smith"], ["John Smith"])
        assert score == pytest.approx(1.0)

    def test_punctuation_insensitive(self) -> None:
        # Commas and dots are stripped
        score = author_similarity(["Smith, J."], ["Smith J"])
        assert score > 0.85

    def test_bonus_for_additional_matching_authors(self) -> None:
        """Having more authors match should yield a higher score than only first-author match."""
        score_first_only = author_similarity(["Smith, John"], ["Smith, John"])
        score_with_bonus = author_similarity(
            ["Smith, John", "Doe, Jane"],
            ["Smith, John", "Doe, Jane"],
        )
        assert score_with_bonus >= score_first_only

    def test_score_capped_at_1_0(self) -> None:
        score = author_similarity(
            ["Smith, John"] * 5,
            ["Smith, John"] * 5,
        )
        assert score <= 1.0

    def test_returns_float_in_0_1_range(self) -> None:
        score = author_similarity(["Alice"], ["Bob"])
        assert 0.0 <= score <= 1.0

    def test_first_author_dominates_over_rest(self) -> None:
        """Different first author but all others match should yield lower score than same first author."""
        score_diff_first = author_similarity(
            ["Adams, Tom", "Smith, John", "Doe, Jane"],
            ["Brown, Alice", "Smith, John", "Doe, Jane"],
        )
        score_same_first = author_similarity(
            ["Smith, John", "Doe, Jane"],
            ["Smith, John", "Other, Person"],
        )
        assert score_same_first > score_diff_first


# ---------------------------------------------------------------------------
# compute_match_score
# ---------------------------------------------------------------------------

class TestComputeMatchScore:
    def test_identical_metadata_returns_high_score(self) -> None:
        score = compute_match_score(
            ref_title="Deep Learning for NLP",
            ref_authors=["Smith, Jane", "Doe, John"],
            ref_year=2020,
            candidate_title="Deep Learning for NLP",
            candidate_authors=["Smith, Jane", "Doe, John"],
            candidate_year=2020,
        )
        assert score > 0.9

    def test_similar_metadata_returns_moderate_score(self) -> None:
        score = compute_match_score(
            ref_title="Neural Network Methods in NLP",
            ref_authors=["Smith, Jane"],
            ref_year=2020,
            candidate_title="Neural Methods in Natural Language Processing",
            candidate_authors=["Smith, J."],
            candidate_year=2021,
        )
        assert 0.4 < score < 0.95

    def test_completely_different_returns_low_score(self) -> None:
        score = compute_match_score(
            ref_title="Quantum Mechanics Principles",
            ref_authors=["Einstein, Albert"],
            ref_year=1905,
            candidate_title="Impressionism in 19th Century Painting",
            candidate_authors=["Monet, Claude"],
            candidate_year=1880,
        )
        assert score < 0.3

    def test_exact_year_contributes_full_year_weight(self) -> None:
        score_exact = compute_match_score(
            ref_title="Paper Title",
            ref_authors=["Author A"],
            ref_year=2020,
            candidate_title="Paper Title",
            candidate_authors=["Author A"],
            candidate_year=2020,
        )
        score_no_year = compute_match_score(
            ref_title="Paper Title",
            ref_authors=["Author A"],
            ref_year=None,
            candidate_title="Paper Title",
            candidate_authors=["Author A"],
            candidate_year=2020,
        )
        # Exact year match should add 0.15 (year_weight=0.15, year_sim=1.0)
        assert score_exact > score_no_year

    def test_off_by_one_year_contributes_half_year_weight(self) -> None:
        score_exact = compute_match_score(
            ref_title="Paper",
            ref_authors=["Author"],
            ref_year=2020,
            candidate_title="Paper",
            candidate_authors=["Author"],
            candidate_year=2020,
        )
        score_off = compute_match_score(
            ref_title="Paper",
            ref_authors=["Author"],
            ref_year=2020,
            candidate_title="Paper",
            candidate_authors=["Author"],
            candidate_year=2021,
        )
        # Difference should be approximately 0.15 * 0.5 = 0.075
        assert score_exact > score_off
        assert abs(score_exact - score_off - 0.075) < 0.01

    def test_none_year_contributes_zero(self) -> None:
        score_with_year = compute_match_score(
            ref_title="Paper",
            ref_authors=["Author"],
            ref_year=2020,
            candidate_title="Paper",
            candidate_authors=["Author"],
            candidate_year=2020,
        )
        score_no_year = compute_match_score(
            ref_title="Paper",
            ref_authors=["Author"],
            ref_year=None,
            candidate_title="Paper",
            candidate_authors=["Author"],
            candidate_year=None,
        )
        # With None years year contributes 0.0; difference = 0.15
        assert abs(score_with_year - score_no_year - 0.15) < 0.01

    def test_none_title_does_not_crash(self) -> None:
        score = compute_match_score(
            ref_title=None,
            ref_authors=["Author"],
            ref_year=2020,
            candidate_title="Some Title",
            candidate_authors=["Author"],
            candidate_year=2020,
        )
        # Title contributes 0.0; authors exact + year exact = 0.30*1.0 + 0.15*1.0 = 0.45
        assert 0.0 <= score <= 1.0

    def test_empty_authors_does_not_crash(self) -> None:
        score = compute_match_score(
            ref_title="Paper",
            ref_authors=[],
            ref_year=2020,
            candidate_title="Paper",
            candidate_authors=[],
            candidate_year=2020,
        )
        # Authors contribute 0.0; title=1.0 * 0.55 + year=1.0 * 0.15 = 0.70
        assert abs(score - 0.70) < 0.01

    def test_score_rounded_to_4_decimal_places(self) -> None:
        score = compute_match_score(
            ref_title="Some arbitrary title",
            ref_authors=["Author Name"],
            ref_year=2019,
            candidate_title="A somewhat different title",
            candidate_authors=["Author Other"],
            candidate_year=2020,
        )
        # round() to 4 places means at most 4 decimal digits
        assert score == round(score, 4)

    def test_score_does_not_exceed_1_0(self) -> None:
        score = compute_match_score(
            ref_title="Identical",
            ref_authors=["Same Author"] * 10,
            ref_year=2020,
            candidate_title="Identical",
            candidate_authors=["Same Author"] * 10,
            candidate_year=2020,
        )
        assert score <= 1.0

    def test_year_far_off_contributes_zero(self) -> None:
        score_diff_year = compute_match_score(
            ref_title="Paper",
            ref_authors=["Author"],
            ref_year=2020,
            candidate_title="Paper",
            candidate_authors=["Author"],
            candidate_year=1990,
        )
        score_no_year = compute_match_score(
            ref_title="Paper",
            ref_authors=["Author"],
            ref_year=None,
            candidate_title="Paper",
            candidate_authors=["Author"],
            candidate_year=None,
        )
        # Both should yield 0.0 for year component
        assert score_diff_year == score_no_year

    def test_weights_sum_correctly(self) -> None:
        """With identical title and authors but no year, score = 0.55 + 0.30 = 0.85."""
        score = compute_match_score(
            ref_title="Exact Title Match",
            ref_authors=["Exact Author"],
            ref_year=None,
            candidate_title="Exact Title Match",
            candidate_authors=["Exact Author"],
            candidate_year=None,
        )
        assert abs(score - 0.85) < 0.01
