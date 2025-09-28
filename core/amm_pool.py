"""
AMM Pool implementation with accurate CPMM mechanics
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional


@dataclass
class AMMPool:
    """
    Constant Product AMM Pool with accurate trade execution

    Implements x*y=k invariant with proper fee mechanics
    """
    name: str
    fee: float  # Fee rate (e.g., 0.0005 for 5bp)
    reserve_x: float  # Token X reserves (e.g., ETH)
    reserve_y: float  # Token Y reserves (e.g., USDC)
    total_volume: float = 0
    total_fees_earned: float = 0
    total_liquidity_tokens: float = 0  # Track total LP tokens
    min_liquidity: float = 1e-8  # Minimum liquidity to prevent division by zero

    def __post_init__(self):
        """Initialize liquidity tokens based on initial reserves"""
        if self.total_liquidity_tokens == 0 and self.reserve_x > 0 and self.reserve_y > 0:
            # Initial liquidity is geometric mean of reserves
            self.total_liquidity_tokens = np.sqrt(self.reserve_x * self.reserve_y)

    @property
    def k(self) -> float:
        """Invariant constant"""
        return self.reserve_x * self.reserve_y

    def calculate_tvl(self, market_price: float = None) -> float:
        """
        Calculate total value locked at given market price

        Args:
            market_price: External market price (USD per X token)
                         If None, uses spot price

        Returns:
            TVL in USD terms
        """
        if market_price is None:
            # Use spot price if no market price given
            market_price = self.spot_price

        # TVL = value of X tokens + value of Y tokens
        # Since Y is already in USD, and X needs to be valued at market price
        return self.reserve_x * market_price + self.reserve_y

    @property
    def tvl(self) -> float:
        """
        Total value locked using spot price

        For backward compatibility, but note this can be misleading
        for imbalanced pools where spot price diverges from market price.
        """
        # Use spot price for backward compatibility
        return self.calculate_tvl(self.spot_price)

    @property
    def spot_price(self) -> float:
        """Current spot price (Y per X)"""
        if self.reserve_x < self.min_liquidity:
            return 0
        return self.reserve_y / self.reserve_x

    def execute_trade(self, trade_size: float, is_buy: bool = True) -> Dict[str, float]:
        """
        Execute a trade and return detailed results
        Updates reserves immediately

        Args:
            trade_size: Amount of input token
            is_buy: True = buying X with Y, False = selling X for Y

        Returns:
            Dict with execution details including output, price, slippage
        """
        # Check minimum liquidity
        if self.reserve_x < self.min_liquidity or self.reserve_y < self.min_liquidity:
            raise ValueError(f"Insufficient liquidity in pool {self.name}")

        if trade_size <= 0:
            return {
                'input': 0,
                'output': 0,
                'execution_price': self.spot_price,
                'spot_price': self.spot_price,
                'slippage': 0,
                'fee_paid': 0,
                'total_cost': 0,
                'post_trade_price': self.spot_price
            }

        # Store original k for verification
        k_original = self.k
        spot_price_original = self.spot_price

        if is_buy:
            # Buying X with Y (Y is input)
            dy_in = trade_size

            # Apply fee to input
            dy_after_fee = dy_in * (1 - self.fee)

            # Calculate output using CPMM formula: dx_out = (x * dy) / (y + dy)
            dx_out = (self.reserve_x * dy_after_fee) / (self.reserve_y + dy_after_fee)

            # Calculate what output would be without fee for accurate fee calculation
            dx_out_no_fee = (self.reserve_x * dy_in) / (self.reserve_y + dy_in)

            # Calculate execution price and slippage
            execution_price = dy_in / dx_out if dx_out > 0 else float('inf')
            slippage = (execution_price / spot_price_original) - 1

            # Fee paid (in input token Y)
            fee_paid = dy_in * self.fee

            # Calculate post-trade state
            new_reserve_x = self.reserve_x - dx_out
            new_reserve_y = self.reserve_y + dy_after_fee
            post_trade_price = new_reserve_y / new_reserve_x if new_reserve_x > self.min_liquidity else float('inf')

            # Verify k invariant (with fee going to LPs, k should increase slightly)
            k_after_trade = new_reserve_x * new_reserve_y
            if k_after_trade < k_original * 0.9999:  # Allow tiny numerical errors
                raise ValueError(f"K invariant violated: {k_original} -> {k_after_trade}")

            result = {
                'input': dy_in,
                'output': dx_out,
                'execution_price': execution_price,
                'spot_price': spot_price_original,
                'slippage': slippage,
                'fee_paid': fee_paid,
                'total_cost': self.fee + slippage,  # Combined cost metric
                'post_trade_price': post_trade_price
            }

            # Update reserves immediately
            self.reserve_x = new_reserve_x
            self.reserve_y = new_reserve_y
            self.total_volume += dy_in
            self.total_fees_earned += fee_paid

        else:
            # Selling X for Y (X is input)
            dx_in = trade_size

            # Apply fee to input
            dx_after_fee = dx_in * (1 - self.fee)

            # Calculate output: dy_out = (y * dx) / (x + dx)
            dy_out = (self.reserve_y * dx_after_fee) / (self.reserve_x + dx_after_fee)

            # Calculate what output would be without fee
            dy_out_no_fee = (self.reserve_y * dx_in) / (self.reserve_x + dx_in)

            # Calculate execution price and slippage
            execution_price = dy_out / dx_in if dx_in > 0 else 0
            slippage = 1 - (execution_price / spot_price_original)

            # Fee paid (convert to Y terms for consistency)
            # The fee is dx_in * fee in X terms
            # In Y terms, this is worth: (dx_in * fee) * execution_price
            # But more accurately, it's the difference in output
            fee_paid_y = dy_out_no_fee - dy_out

            # Calculate post-trade state
            new_reserve_x = self.reserve_x + dx_after_fee
            new_reserve_y = self.reserve_y - dy_out
            post_trade_price = new_reserve_y / new_reserve_x if new_reserve_x > self.min_liquidity else 0

            # Verify k invariant
            k_after_trade = new_reserve_x * new_reserve_y
            if k_after_trade < k_original * 0.9999:
                raise ValueError(f"K invariant violated: {k_original} -> {k_after_trade}")

            result = {
                'input': dx_in,
                'output': dy_out,
                'execution_price': execution_price,
                'spot_price': spot_price_original,
                'slippage': slippage,
                'fee_paid': fee_paid_y,  # In Y terms
                'total_cost': self.fee + slippage,
                'post_trade_price': post_trade_price
            }

            # Update reserves immediately
            self.reserve_x = new_reserve_x
            self.reserve_y = new_reserve_y
            self.total_volume += dy_out  # Volume in Y terms
            self.total_fees_earned += fee_paid_y

        return result

    def add_liquidity(self, amount_x: float, amount_y: float) -> Dict[str, float]:
        """
        Add liquidity to the pool

        Args:
            amount_x: Amount of token X to add
            amount_y: Amount of token Y to add

        Returns:
            Dict with liquidity tokens minted and actual amounts added
        """
        if amount_x <= 0 or amount_y <= 0:
            return {'liquidity_tokens': 0, 'actual_x': 0, 'actual_y': 0}

        # First LP gets to set the ratio
        if self.total_liquidity_tokens == 0:
            liquidity_tokens = np.sqrt(amount_x * amount_y)
            actual_x = amount_x
            actual_y = amount_y
        else:
            # Subsequent LPs must match the ratio
            current_ratio = self.reserve_y / self.reserve_x
            optimal_y = amount_x * current_ratio

            if amount_y >= optimal_y:
                # X is the limiting factor
                actual_x = amount_x
                actual_y = optimal_y
            else:
                # Y is the limiting factor
                actual_x = amount_y / current_ratio
                actual_y = amount_y

            # Mint liquidity tokens proportionally
            liquidity_tokens = (actual_x / self.reserve_x) * self.total_liquidity_tokens

        # Update reserves
        self.reserve_x += actual_x
        self.reserve_y += actual_y
        self.total_liquidity_tokens += liquidity_tokens

        return {
            'liquidity_tokens': liquidity_tokens,
            'actual_x': actual_x,
            'actual_y': actual_y
        }

    def remove_liquidity(self, liquidity_tokens: float) -> Dict[str, float]:
        """
        Remove liquidity from the pool

        Args:
            liquidity_tokens: Amount of liquidity tokens to burn

        Returns:
            Dict with amounts of X and Y returned
        """
        if liquidity_tokens <= 0 or liquidity_tokens > self.total_liquidity_tokens:
            return {'amount_x': 0, 'amount_y': 0}

        # Calculate proportional share
        share = liquidity_tokens / self.total_liquidity_tokens

        # Calculate amounts to return
        amount_x = self.reserve_x * share
        amount_y = self.reserve_y * share

        # Update reserves
        self.reserve_x -= amount_x
        self.reserve_y -= amount_y
        self.total_liquidity_tokens -= liquidity_tokens

        # Ensure minimum liquidity remains
        if self.reserve_x < self.min_liquidity:
            self.reserve_x = self.min_liquidity
        if self.reserve_y < self.min_liquidity:
            self.reserve_y = self.min_liquidity
        if self.total_liquidity_tokens < self.min_liquidity:
            self.total_liquidity_tokens = self.min_liquidity

        return {
            'amount_x': amount_x,
            'amount_y': amount_y
        }


def get_best_execution(pools: List[AMMPool], trade_size: float, is_buy: bool = True) -> Tuple[Optional[AMMPool], Optional[Dict]]:
    """
    Find the pool offering best execution for a given trade

    Args:
        pools: List of AMM pools
        trade_size: Size of trade
        is_buy: Direction of trade

    Returns:
        Tuple of (best_pool, execution_details)
    """
    best_pool = None
    best_result = None
    best_output = 0

    for pool in pools:
        try:
            result = pool.execute_trade(trade_size, is_buy)

            # We want maximum output regardless of direction
            if result['output'] > best_output:
                best_output = result['output']
                best_pool = pool
                best_result = result
        except ValueError:
            # Skip pools with insufficient liquidity
            continue

    return best_pool, best_result


def get_all_quotes(pools: List[AMMPool], trade_size: float, is_buy: bool = True) -> Dict[str, Dict]:
    """
    Get execution quotes from all pools for a given trade

    Args:
        pools: List of AMM pools
        trade_size: Size of trade
        is_buy: Direction of trade

    Returns:
        Dict mapping pool name to execution details
    """
    quotes = {}
    for pool in pools:
        try:
            quotes[pool.name] = pool.execute_trade(trade_size, is_buy)
        except ValueError:
            # Skip pools with insufficient liquidity
            continue
    return quotes