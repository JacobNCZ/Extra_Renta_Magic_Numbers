"""Zpětně kompatibilní fasáda pro datové modely."""

from __future__ import annotations

from .config_models import (  # noqa: F401
    AppConfig,
    DiversityConfig,
    ExportConfig,
    GeneratorConfig,
    HardFilterConfig,
    MMRConfig,
    ScoringConfig,
)
from .domain_models import (  # noqa: F401
    CombinationCandidate,
    CombinationMetrics,
    FilterResult,
    ScoreBreakdown,
    SelectionBreakdown,
)
from .history_models import HistoricalContext, HistoricalDraw, NumberTuple  # noqa: F401
from .stats_models import (  # noqa: F401
    BenchmarkStats,
    DiversityDiagnostics,
    DiversitySelectionResult,
    RunStats,
)

__all__ = [
    "AppConfig",
    "BenchmarkStats",
    "CombinationCandidate",
    "CombinationMetrics",
    "DiversityConfig",
    "DiversityDiagnostics",
    "DiversitySelectionResult",
    "ExportConfig",
    "FilterResult",
    "GeneratorConfig",
    "HardFilterConfig",
    "HistoricalContext",
    "HistoricalDraw",
    "MMRConfig",
    "NumberTuple",
    "RunStats",
    "ScoreBreakdown",
    "ScoringConfig",
    "SelectionBreakdown",
]
