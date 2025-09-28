"""
Core modules for AMM simulation and dynamic fee optimization
"""

from .amm_pool import AMMPool
from .cex_arbitrage import CEXArbitrageur, ArbitrageOpportunity, calculate_arbitrage_volume
from .trader_agents import TraderAgent, TraderType, TraderProfile, TRADER_PROFILES, create_trader_population
from .lp_agents import LPAgent, LPType, LPProfile, PassiveLP, ActiveLP, create_lp_population, PoolInfo
from .dynamic_fee_engine import (
    calculate_dynamic_fee,
    initialize_dynamic_fee_state,
    update_dynamic_fees_daily,
    calculate_fee_adjustment
)

__all__ = [
    # AMM components
    'AMMPool',

    # Arbitrage
    'CEXArbitrageur',
    'ArbitrageOpportunity',
    'calculate_arbitrage_volume',

    # Trader agents
    'TraderAgent',
    'TraderType',
    'TraderProfile',
    'TRADER_PROFILES',
    'create_trader_population',

    # LP agents
    'LPAgent',
    'LPType',
    'LPProfile',
    'PassiveLP',
    'ActiveLP',
    'create_lp_population',
    'PoolInfo',

    # Dynamic fee optimization (pure algorithms)
    'calculate_dynamic_fee',
    'initialize_dynamic_fee_state',
    'update_dynamic_fees_daily',
    'calculate_fee_adjustment'
]