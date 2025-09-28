"""
CEX-AMM Arbitrage Calculator
Calculates and executes optimal arbitrage between CEX and AMM pools
"""

import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from .amm_pool import AMMPool


@dataclass
class ArbitrageOpportunity:
    """Details of an arbitrage opportunity"""
    direction: str  # 'buy_from_amm' or 'sell_to_amm'
    cex_price: float
    amm_price_before: float
    amm_price_after: float
    trade_size_eth: float
    trade_size_usd: float
    profit_usd: float
    cex_fee_usd: float
    amm_fee_usd: float


class CEXArbitrageur:
    """
    Arbitrageur that trades between CEX and AMM to capture price differences

    Conventions:
    - AMM pool: X = ETH, Y = USD
    - CEX price: USD per ETH
    - Positive trade: Buy from AMM (remove ETH)
    - Negative trade: Sell to AMM (add ETH)
    """

    def __init__(self, cex_fee: float = 0.001, max_capital: float = 100_000):
        """
        Args:
            cex_fee: CEX trading fee (e.g., 0.001 = 0.1%)
            max_capital: Maximum capital available for arbitrage in USD
        """
        self.cex_fee = cex_fee
        self.max_capital = max_capital

    def calculate_arbitrage(self, pool: AMMPool, cex_price: float) -> Optional[ArbitrageOpportunity]:
        """
        Calculate optimal arbitrage trade between CEX and AMM

        This finds the trade that equalizes prices between CEX and AMM after fees

        Args:
            pool: AMM pool to arbitrage
            cex_price: Current CEX price (USD per ETH)

        Returns:
            ArbitrageOpportunity if profitable, None otherwise
        """

        # Get current AMM price
        amm_price = pool.spot_price  # USD per ETH

        # Check if arbitrage exists
        if abs(amm_price - cex_price) / cex_price < 0.0001:  # Less than 0.01% difference
            return None

        # Translate cpmm_engine formulas to our convention
        # In cpmm_engine: X=USD, Y=ETH, P=X/Y
        # In our world: X=ETH, Y=USD, P=Y/X

        # We need to find the ETH trade amount that equalizes prices

        if amm_price > cex_price:
            # ETH is expensive on AMM
            # Strategy: Buy ETH from CEX, sell to AMM
            direction = 'sell_to_amm'

            # Calculate optimal trade size using the arbitrage formula
            # After trade, we want: amm_price_new = cex_price * (1 + margins)

            # From cpmm_engine (adapted):
            # We want to find ETH amount to sell that equalizes prices

            # The formula from cpmm_engine, translated:
            # Original: Y * (1 - sqrt((P_amm * (1 - fee_amm)) / (P_cex * (1 + fee_cex))))
            # Where Y is ETH reserves

            # In our convention:
            ratio = (amm_price * (1 - pool.fee)) / (cex_price * (1 + self.cex_fee))

            if ratio <= 0:
                return None

            # Calculate ETH to sell to AMM
            eth_amount = pool.reserve_x * (1 - np.sqrt(1/ratio))

            # Apply realistic constraints
            # 1. Limited by capital available
            max_capital_eth = self.max_capital / cex_price
            # 2. Limited by pool impact (0.1% of reserves)
            max_pool_impact = pool.reserve_x * 0.001
            # 3. Limited by reasonable trade size
            max_trade_size = min(1000 / cex_price, 0.1)  # Max $1000 or 0.1 ETH

            eth_amount = min(eth_amount, max_capital_eth, max_pool_impact, max_trade_size)

            if eth_amount <= 0:
                return None

        else:
            # ETH is cheap on AMM
            # Strategy: Buy ETH from AMM, sell to CEX
            direction = 'buy_from_amm'

            # Calculate optimal trade size
            ratio = (amm_price * (1 + pool.fee)) / (cex_price * (1 - self.cex_fee))

            if ratio <= 0:
                return None

            # Calculate ETH to buy from AMM
            eth_amount = pool.reserve_x * (np.sqrt(1/ratio) - 1)

            if eth_amount <= 0:
                return None

            # Apply realistic constraints
            # 1. Limited by capital available for buying
            max_capital_eth = self.max_capital / (cex_price * (1 + pool.fee))
            # 2. Limited by pool impact (0.1% of reserves)
            max_pool_impact = pool.reserve_x * 0.001
            # 3. Limited by reasonable trade size
            max_trade_size = min(1000 / cex_price, 0.1)  # Max $1000 or 0.1 ETH

            eth_amount = min(eth_amount, max_capital_eth, max_pool_impact, max_trade_size)

        # Simulate the trade to get exact numbers
        opportunity = self._simulate_arbitrage(pool, cex_price, eth_amount, direction)

        return opportunity if opportunity and opportunity.profit_usd > 0 else None

    def _simulate_arbitrage(self, pool: AMMPool, cex_price: float,
                           eth_amount: float, direction: str) -> Optional[ArbitrageOpportunity]:
        """
        Simulate an arbitrage trade and calculate profit

        Args:
            pool: AMM pool
            cex_price: CEX price
            eth_amount: Amount of ETH to trade
            direction: 'buy_from_amm' or 'sell_to_amm'

        Returns:
            ArbitrageOpportunity with details
        """

        amm_price_before = pool.spot_price

        if direction == 'sell_to_amm':
            # Selling ETH to AMM
            # First, buy ETH from CEX
            cex_cost = eth_amount * cex_price * (1 + self.cex_fee)

            # Then sell to AMM (this is a sell in our convention)
            # Create temporary pool to simulate
            temp_pool = AMMPool(
                name="temp",
                fee=pool.fee,
                reserve_x=pool.reserve_x,
                reserve_y=pool.reserve_y
            )

            result = temp_pool.execute_trade(eth_amount, is_buy=False)
            amm_revenue = result['output']  # USD received
            amm_fee = result['fee_paid']

            profit = amm_revenue - cex_cost
            trade_size_usd = cex_cost
            amm_price_after = temp_pool.spot_price

        else:  # buy_from_amm
            # Buying ETH from AMM
            # Create temporary pool to simulate
            temp_pool = AMMPool(
                name="temp",
                fee=pool.fee,
                reserve_x=pool.reserve_x,
                reserve_y=pool.reserve_y
            )

            # Calculate exact USD needed for eth_amount of ETH output
            # From AMM formula: dx_out = (reserve_x * dy_after_fee) / (reserve_y + dy_after_fee)
            # Solving for dy_after_fee: dy_after_fee = (dx_out * reserve_y) / (reserve_x - dx_out)
            # And dy_in = dy_after_fee / (1 - fee)

            if eth_amount >= pool.reserve_x:  # Can't buy all the ETH
                return None

            dy_after_fee = (eth_amount * pool.reserve_y) / (pool.reserve_x - eth_amount)
            usd_needed = dy_after_fee / (1 - pool.fee)

            # Execute the trade
            result = temp_pool.execute_trade(usd_needed, is_buy=True)

            amm_cost = result['input']
            amm_fee = result['fee_paid']
            actual_eth = result['output']

            # Sell to CEX
            cex_revenue = actual_eth * cex_price * (1 - self.cex_fee)

            profit = cex_revenue - amm_cost
            trade_size_usd = amm_cost
            amm_price_after = temp_pool.spot_price

        return ArbitrageOpportunity(
            direction=direction,
            cex_price=cex_price,
            amm_price_before=amm_price_before,
            amm_price_after=amm_price_after,
            trade_size_eth=eth_amount,
            trade_size_usd=trade_size_usd,
            profit_usd=profit,
            cex_fee_usd=trade_size_usd * self.cex_fee if direction == 'sell_to_amm' else cex_revenue * self.cex_fee / (1 - self.cex_fee),
            amm_fee_usd=amm_fee
        )

    def execute_arbitrage(self, pool: AMMPool, cex_price: float,
                         min_profit: float = 0.01) -> Tuple[bool, Optional[ArbitrageOpportunity]]:
        """
        Calculate and execute arbitrage if profitable

        Args:
            pool: AMM pool to arbitrage
            cex_price: Current CEX price
            min_profit: Minimum profit threshold in USD

        Returns:
            Tuple of (executed, opportunity)
        """

        opportunity = self.calculate_arbitrage(pool, cex_price)

        if opportunity and opportunity.profit_usd >= min_profit:
            # Execute the trade on the actual pool
            if opportunity.direction == 'sell_to_amm':
                # Sell ETH to AMM
                pool.execute_trade(opportunity.trade_size_eth, is_buy=False)
            else:
                # Buy ETH from AMM
                # Use the USD amount from simulation
                pool.execute_trade(opportunity.trade_size_usd, is_buy=True)

            return True, opportunity

        return False, opportunity

    def find_equilibrium_price(self, pool: AMMPool, cex_price: float) -> float:
        """
        Find the AMM price that would eliminate arbitrage

        Args:
            pool: AMM pool
            cex_price: CEX price

        Returns:
            Equilibrium AMM price
        """

        # The equilibrium depends on fees
        # If we're selling to AMM: amm_price = cex_price * (1 + cex_fee) / (1 - amm_fee)
        # If we're buying from AMM: amm_price = cex_price * (1 - cex_fee) / (1 + amm_fee)

        # The actual equilibrium is between these bounds
        upper_bound = cex_price * (1 + self.cex_fee) / (1 - pool.fee)
        lower_bound = cex_price * (1 - self.cex_fee) / (1 + pool.fee)

        # Return midpoint as estimate
        return (upper_bound + lower_bound) / 2


def calculate_arbitrage_volume(pool: AMMPool, cex_price: float, cex_fee: float = 0.001) -> Dict[str, float]:
    """
    Quick function to calculate arbitrage volume and profit

    Args:
        pool: AMM pool
        cex_price: CEX price in USD/ETH
        cex_fee: CEX fee rate

    Returns:
        Dict with arbitrage details
    """

    arbitrageur = CEXArbitrageur(cex_fee)
    opportunity = arbitrageur.calculate_arbitrage(pool, cex_price)

    if opportunity:
        return {
            'direction': opportunity.direction,
            'eth_volume': opportunity.trade_size_eth,
            'usd_volume': opportunity.trade_size_usd,
            'profit': opportunity.profit_usd,
            'amm_price_before': opportunity.amm_price_before,
            'amm_price_after': opportunity.amm_price_after,
            'price_impact': (opportunity.amm_price_after - opportunity.amm_price_before) / opportunity.amm_price_before
        }
    else:
        return {
            'direction': 'none',
            'eth_volume': 0,
            'usd_volume': 0,
            'profit': 0,
            'amm_price_before': pool.spot_price,
            'amm_price_after': pool.spot_price,
            'price_impact': 0
        }