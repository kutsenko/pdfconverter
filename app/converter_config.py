"""Configuration for PDF converter optimization settings."""

import os
from dataclasses import dataclass


@dataclass
class OptimizerConfig:
    """OCRmyPDF optimization configuration by PDF type."""

    text_only_optimize: int = 1
    scanned_optimize: int = 1
    mixed_optimize: int = 1
    unknown_optimize: int = 0

    # Threading configuration
    max_workers: int = 8
    ocrmypdf_jobs: int = 4

    # PDF/A version: 1 for PDF/A-1b, 2 for PDF/A-2b
    pdfa_version: int = 2

    def __post_init__(self) -> None:
        """Validate configuration values."""
        for field in (
            "text_only_optimize",
            "scanned_optimize",
            "mixed_optimize",
            "unknown_optimize",
        ):
            value = getattr(self, field)
            if not 0 <= value <= 3:
                raise ValueError(f"{field} must be between 0 and 3, got {value}")

        if self.max_workers < 1:
            raise ValueError(f"max_workers must be >= 1, got {self.max_workers}")
        if self.ocrmypdf_jobs < 1:
            raise ValueError(f"ocrmypdf_jobs must be >= 1, got {self.ocrmypdf_jobs}")
        if self.pdfa_version not in (1, 2):
            raise ValueError(
                f"pdfa_version must be 1 or 2, got {self.pdfa_version}"
            )

    @classmethod
    def from_environment(cls) -> "OptimizerConfig":
        """Load configuration from environment variables."""
        env_mapping = {
            "text_only_optimize": "PDF_TEXT_OPTIMIZE",
            "scanned_optimize": "PDF_SCANNED_OPTIMIZE",
            "mixed_optimize": "PDF_MIXED_OPTIMIZE",
            "unknown_optimize": "PDF_UNKNOWN_OPTIMIZE",
            "max_workers": "OCR_MAX_WORKERS",
            "ocrmypdf_jobs": "OCRMYPDF_JOBS",
            "pdfa_version": "PDFA_VERSION",
        }
        defaults = {
            "text_only_optimize": "1",
            "scanned_optimize": "1",
            "mixed_optimize": "1",
            "unknown_optimize": "0",
            "max_workers": "8",
            "ocrmypdf_jobs": "4",
            "pdfa_version": "2",
        }

        kwargs = {}
        for field, env_var in env_mapping.items():
            raw = os.getenv(env_var, defaults[field])
            try:
                kwargs[field] = int(raw)
            except (TypeError, ValueError) as e:
                raise ValueError(
                    f"Invalid value for {env_var}: {raw!r} (must be an integer)"
                ) from e

        return cls(**kwargs)


_config = OptimizerConfig.from_environment()


def get_optimizer_config() -> OptimizerConfig:
    """Get current optimizer configuration."""
    return _config
