"""
Simple arbitrage implementation that maintains TVL conservation.
Arbitrage only moves value between pools, it doesn't create value.
"""

import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ArbitrageResult:
    """Result of an arbitrage execution"""
    executed: bool
    direction: str  # 'none', 'cex_to_amm', 'amm_to_cex'
    volume_usd: float
    profit_usd: float
    price_impact: float


def calculate_simple_arbitrage(pool, cex_price: float, max_trade_pct: float = 0.001) -> ArbitrageResult:
    """
    Calculate and execute simple arbitrage that maintains TVL conservation.

    This implementation ensures arbitrage only rebalances prices without creating value.
    The arbitrageur profits from the price difference but doesn't add net value to the system.

    Args:
        pool: AMM pool to arbitrage
        cex_price: CEX price in USD/ETH
        max_trade_pct: Maximum trade as percentage of pool (0.001 = 0.1%)

    Returns:
        ArbitrageResult with execution details
    """

    # Get current AMM price
    amm_price = pool.spot_price

    # Check if arbitrage opportunity exists (>0.1% price difference)
    price_diff_pct = abs(amm_price - cex_price) / cex_price
    if price_diff_pct < 0.001:
        return ArbitrageResult(False, 'none', 0, 0, 0)

    # Calculate maximum trade size (0.1% of pool reserves)
    max_eth_trade = pool.reserve_x * max_trade_pct
    max_usd_trade = pool.reserve_y * max_trade_pct

    if amm_price > cex_price:
        # AMM price too high - sell ETH to AMM to push price down
        # But we limit the trade size to avoid massive impact

        # Calculate trade size to move price 10% toward CEX price
        # This prevents trying to equalize in one massive trade
        target_price = amm_price - (amm_price - cex_price) * 0.1

        # From CPMM formula: to reach target price, we need specific ETH amount
        # New price = (Y + dy) / (X - dx) where dx is ETH we remove
        # Solving: dx = X - Y/target_price (simplified)
        eth_needed = pool.reserve_x - pool.reserve_y / target_price

        # Apply constraints
        eth_trade = min(eth_needed, max_eth_trade, 0.01)  # Max 0.01 ETH per trade

        if eth_trade > 0:
            # Execute: Sell ETH to AMM
            result = pool.execute_trade(eth_trade, is_buy=False)

            # Estimate profit (price difference * volume * 0.5 for average execution)
            profit = (amm_price - cex_price) * eth_trade * 0.3  # 30% capture of spread

            return ArbitrageResult(
                executed=True,
                direction='cex_to_amm',
                volume_usd=eth_trade * cex_price,
                profit_usd=profit,
                price_impact=(pool.spot_price - amm_price) / amm_price
            )

    else:
        # AMM price too low - buy ETH from AMM to push price up

        # Calculate trade size to move price 10% toward CEX price
        target_price = amm_price + (cex_price - amm_price) * 0.1

        # Calculate USD needed for target
        # From formula: Y needed = X * target_price
        # Amount to add: dy = X * target_price - Y
        usd_needed = pool.reserve_x * target_price - pool.reserve_y

        # Apply constraints
        usd_trade = min(abs(usd_needed), max_usd_trade, 100)  # Max $100 per trade

        if usd_trade > 0:
            # Execute: Buy ETH from AMM
            result = pool.execute_trade(usd_trade, is_buy=True)

            # Estimate profit
            eth_received = result['output']
            profit = (cex_price - amm_price) * eth_received * 0.3  # 30% capture

            return ArbitrageResult(
                executed=True,
                direction='amm_to_cex',
                volume_usd=usd_trade,
                profit_usd=profit,
                price_impact=(pool.spot_price - amm_price) / amm_price
            )

    return ArbitrageResult(False, 'none', 0, 0, 0)