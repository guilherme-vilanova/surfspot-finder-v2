from typing import Callable, Dict

from .classic import ClassicHeuristicRanking
from .ports import RankingStrategy

STRATEGIES: Dict[str, Callable[[], RankingStrategy]] = {
    "classic": ClassicHeuristicRanking,
}


def build_ranking_strategy(name: str = "classic") -> RankingStrategy:
    """Build a ranking strategy by name (usually from RANKING_STRATEGY env var).

    To try a new scoring model: add a class implementing RankingStrategy,
    register it here, then flip the env var. No changes needed in services/
    or Flask routes.
    """
    try:
        factory = STRATEGIES[name]
    except KeyError as exc:
        available = ", ".join(sorted(STRATEGIES)) or "none"
        raise ValueError(f"Unknown ranking strategy '{name}'. Available: {available}.") from exc
    return factory()
