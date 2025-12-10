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

    @classmethod
    def from_environment(cls) -> "OptimizerConfig":
        """Load configuration from environment variables."""
        return cls(
            text_only_optimize=int(os.getenv("PDF_TEXT_OPTIMIZE", "1")),
            scanned_optimize=int(os.getenv("PDF_SCANNED_OPTIMIZE", "1")),
            mixed_optimize=int(os.getenv("PDF_MIXED_OPTIMIZE", "1")),
            unknown_optimize=int(os.getenv("PDF_UNKNOWN_OPTIMIZE", "0")),
        )


_config = OptimizerConfig.from_environment()


def get_optimizer_config() -> OptimizerConfig:
    """Get current optimizer configuration."""
    return _config
