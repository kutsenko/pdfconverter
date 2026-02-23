from unittest.mock import patch

import pytest

from app.converter_config import OptimizerConfig


class TestOptimizerConfigDefaults:
    """Tests for OptimizerConfig default values."""

    def test_default_values(self):
        config = OptimizerConfig()
        assert config.text_only_optimize == 1
        assert config.scanned_optimize == 1
        assert config.mixed_optimize == 1
        assert config.unknown_optimize == 0
        assert config.max_workers == 8
        assert config.ocrmypdf_jobs == 4

    def test_custom_valid_values(self):
        config = OptimizerConfig(
            text_only_optimize=3,
            scanned_optimize=2,
            mixed_optimize=0,
            unknown_optimize=0,
            max_workers=16,
            ocrmypdf_jobs=8,
        )
        assert config.text_only_optimize == 3
        assert config.max_workers == 16


class TestOptimizerConfigValidation:
    """Tests for OptimizerConfig __post_init__ validation."""

    @pytest.mark.parametrize(
        "field",
        [
            "text_only_optimize",
            "scanned_optimize",
            "mixed_optimize",
            "unknown_optimize",
        ],
    )
    def test_optimize_level_too_high(self, field):
        with pytest.raises(ValueError, match="must be between 0 and 3"):
            OptimizerConfig(**{field: 4})

    @pytest.mark.parametrize(
        "field",
        [
            "text_only_optimize",
            "scanned_optimize",
            "mixed_optimize",
            "unknown_optimize",
        ],
    )
    def test_optimize_level_negative(self, field):
        with pytest.raises(ValueError, match="must be between 0 and 3"):
            OptimizerConfig(**{field: -1})

    def test_max_workers_zero(self):
        with pytest.raises(ValueError, match="max_workers must be >= 1"):
            OptimizerConfig(max_workers=0)

    def test_ocrmypdf_jobs_zero(self):
        with pytest.raises(ValueError, match="ocrmypdf_jobs must be >= 1"):
            OptimizerConfig(ocrmypdf_jobs=0)

    def test_boundary_values_valid(self):
        config = OptimizerConfig(
            text_only_optimize=0,
            scanned_optimize=3,
            max_workers=1,
            ocrmypdf_jobs=1,
        )
        assert config.text_only_optimize == 0
        assert config.scanned_optimize == 3


class TestOptimizerConfigFromEnvironment:
    """Tests for OptimizerConfig.from_environment()."""

    @patch.dict("os.environ", {"PDF_TEXT_OPTIMIZE": "not_a_number"})
    def test_invalid_env_var_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid value for PDF_TEXT_OPTIMIZE"):
            OptimizerConfig.from_environment()

    @patch.dict("os.environ", {"OCR_MAX_WORKERS": "0"})
    def test_env_var_out_of_range(self):
        with pytest.raises(ValueError, match="max_workers must be >= 1"):
            OptimizerConfig.from_environment()

    @patch.dict("os.environ", {}, clear=True)
    def test_defaults_from_environment(self):
        config = OptimizerConfig.from_environment()
        assert config.text_only_optimize == 1
        assert config.unknown_optimize == 0
        assert config.max_workers == 8
