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

# Configuration integration
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import POOL_CONFIGS


def get_pool_config(pool_type: str) -> dict:
    """
    Get configuration parameters for a specific pool type.

    Args:
        pool_type: 'stable', 'standard', or 'volatile'

    Returns:
        Dictionary with pool configuration parameters
    """
    if pool_type not in POOL_CONFIGS:
        raise ValueError(f"Unknown pool type: {pool_type}. Available: {list(POOL_CONFIGS.keys())}")
    return POOL_CONFIGS[pool_type]


def create_pool_config_tuple(config: dict) -> tuple:
    """
    Convert pool config dictionary to tuple format expected by dynamic fee engine.

    Args:
        config: Pool configuration dictionary

    Returns:
        Tuple in format: (linear_slope, alpha, max_fee_delta, tolerance, initial_fee, min_fee, max_fee, max_adjustment_rate)
    """
    return (
        config['linear_slope'],
        config['alpha'],
        config['max_fee_delta'],
        config['tolerance'],
        config['initial_fee'],
        config['min_fee'],
        config['max_fee'],
        config['max_adjustment_rate']
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
    'calculate_fee_adjustment',

    # Configuration
    'POOL_CONFIGS',
    'get_pool_config',
    'create_pool_config_tuple'
]