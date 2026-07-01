"""Surf condition ranking, isolated from providers and Flask.

This package only knows about plain dicts (marine/forecast readings, beach
metadata) and numbers in/out - no HTTP, no Flask, no caching. That is what
lets the scoring model change frequently (new heuristic, weighting tweak, or
eventually a learned model) without risk to the rest of the app.
"""

from .factory import build_ranking_strategy
from .ports import RankingStrategy, ScoreBreakdown

__all__ = ["build_ranking_strategy", "RankingStrategy", "ScoreBreakdown"]
