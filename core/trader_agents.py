"""
Trader Agent Framework for Market Simulations
Three trader types: Arbitrageur, Retail, and Whale
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


class TraderType(Enum):
    """Different types of traders with distinct behaviors"""
    ARBITRAGEUR = "arb"        # CEX-AMM arbitrage
    RETAIL = "retail"          # Small trades
    WHALE = "whale"            # Large trades


@dataclass
class TraderProfile:
    """Configuration for a trader agent"""
    trader_type: TraderType
    avg_trade_size: float           # Average trade size in USD
    trade_size_std: float          # Standard deviation (for log-normal)
    min_trade_size: float         # Minimum viable trade
    max_trade_size: float         # Maximum single trade


class TraderAgent:
    """Base class for trader agents"""

    def __init__(self, profile: TraderProfile):
        self.profile = profile
        self.trades_executed = 0
        self.total_volume = 0

    def generate_trade_size(self, opportunity_size: Optional[float] = None) -> float:
        """
        Generate a trade size based on trader profile

        Args:
            opportunity_size: For arbitrageurs, the profitable trade size

        Returns:
            Trade size in USD
        """
        if self.profile.trader_type == TraderType.ARBITRAGEUR:
            # Arbitrageurs trade the exact opportunity size to maximize profit
            if opportunity_size is not None:
                return opportunity_size
            else:
                # No opportunity, no trade
                return 0

        elif self.profile.trader_type == TraderType.RETAIL:
            # Small, relatively consistent trades
            size = np.random.lognormal(
                np.log(self.profile.avg_trade_size),
                self.profile.trade_size_std
            )

        elif self.profile.trader_type == TraderType.WHALE:
            # Large trades with high variance
            size = np.random.lognormal(
                np.log(self.profile.avg_trade_size),
                self.profile.trade_size_std
            )

        else:
            raise ValueError(f"Unknown trader type: {self.profile.trader_type}")

        # Apply bounds
        return np.clip(size, self.profile.min_trade_size, self.profile.max_trade_size)

    def evaluate_execution(self, quotes: Dict[str, float]) -> Optional[str]:
        """
        Evaluate quotes and choose best pool for execution
        Simply returns the pool with the highest output

        Args:
            quotes: Dict mapping pool names to output amounts

        Returns:
            Name of chosen pool or None if no quotes
        """
        if not quotes:
            return None

        # Simple: take the best output
        best_pool = max(quotes, key=quotes.get)
        return best_pool

    def should_trade(self, has_opportunity: bool = False) -> bool:
        """
        Decide whether to trade

        Args:
            has_opportunity: For arbitrageurs, whether profitable opportunity exists

        Returns:
            Boolean decision to trade
        """
        if self.profile.trader_type == TraderType.ARBITRAGEUR:
            # Only trade if arbitrage opportunity exists
            return has_opportunity

        elif self.profile.trader_type == TraderType.RETAIL:
            # Regular trading pattern
            return np.random.random() < 0.7

        elif self.profile.trader_type == TraderType.WHALE:
            # Less frequent, more strategic
            return np.random.random() < 0.2

        else:
            return False

    def record_trade(self, volume: float):
        """Record a completed trade"""
        self.trades_executed += 1
        self.total_volume += volume


# Predefined trader profiles
TRADER_PROFILES = {
    'arbitrageur': TraderProfile(
        trader_type=TraderType.ARBITRAGEUR,
        avg_trade_size=0,  # Dynamic based on opportunity
        trade_size_std=0,  # Not used for arbitrageurs
        min_trade_size=0,  # No minimum for arbitrageurs
        max_trade_size=float('inf')  # No maximum for arbitrageurs
    ),
    'retail': TraderProfile(
        trader_type=TraderType.RETAIL,
        avg_trade_size=100,
        trade_size_std=0.3,
        min_trade_size=10,
        max_trade_size=1_000
    ),
    'whale': TraderProfile(
        trader_type=TraderType.WHALE,
        avg_trade_size=500_000,
        trade_size_std=0.6,
        min_trade_size=100_000,
        max_trade_size=10_000_000
    )
}


def create_trader_population(distribution: Dict[str, int]) -> List[TraderAgent]:
    """
    Create a population of trader agents

    Args:
        distribution: Dict mapping profile names to counts
                     e.g., {'arbitrageur': 5, 'retail': 100, 'whale': 3}

    Returns:
        List of TraderAgent instances
    """
    traders = []

    for profile_name, count in distribution.items():
        if profile_name in TRADER_PROFILES:
            profile = TRADER_PROFILES[profile_name]
            for _ in range(count):
                traders.append(TraderAgent(profile))
        else:
            raise ValueError(f"Unknown trader profile: {profile_name}")

    return traders