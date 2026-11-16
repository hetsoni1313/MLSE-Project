"""Tests for label validation and normalization."""

from llmops_governance.core.constants import BANKING77_LABEL_SET
from llmops_governance.utils.validation import (
    extract_label_from_response,
    normalize_label,
    validate_label,
)


class TestNormalizeLabel:
    """Test label normalization."""

    def test_already_normalized(self):
        assert normalize_label("change_pin") == "change_pin"

    def test_uppercase(self):
        assert normalize_label("CHANGE_PIN") == "change_pin"

    def test_mixed_case(self):
        assert normalize_label("Change_Pin") == "change_pin"

    def test_whitespace(self):
        assert normalize_label("  change_pin  ") == "change_pin"

    def test_hyphens_to_underscores(self):
        assert normalize_label("change-pin") == "change_pin"

    def test_spaces_to_underscores(self):
        assert normalize_label("change pin") == "change_pin"

    def test_quoted_label(self):
        result = normalize_label('"change_pin"')
        assert result == "change_pin"

    def test_prefix_stripped(self):
        result = normalize_label("Intent: change_pin")
        assert result == "change_pin"

    def test_numbered_prefix(self):
        result = normalize_label("1. change_pin")
        assert result == "change_pin"


class TestValidateLabel:
    """Test label validation against Banking77 set."""

    def test_valid_label(self):
        assert validate_label("change_pin") is True

    def test_invalid_label(self):
        assert validate_label("nonexistent_label") is False

    def test_empty_label(self):
        assert validate_label("") is False

    def test_all_77_labels_are_valid(self, banking77_labels):
        for label in banking77_labels:
            assert validate_label(label) is True, f"{label} should be valid"

    def test_label_set_has_77_entries(self):
        assert len(BANKING77_LABEL_SET) >= 77


class TestExtractLabel:
    """Test label extraction from LLM responses."""

    def test_clean_label(self):
        result = extract_label_from_response("change_pin")
        assert result == "change_pin"

    def test_with_explanation(self):
        result = extract_label_from_response(
            "The intent is change_pin because the user wants to change their PIN."
        )
        # Should extract the label
        assert "change_pin" in result or result == "change_pin"
