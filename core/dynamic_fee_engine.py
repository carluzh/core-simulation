"""
Dynamic Fee Algorithm Engine
Pure algorithmic implementation for fee optimization
"""

import numpy as np
from numba import njit
from typing import Tuple


@njit
def initialize_dynamic_fee_state(M, pool_config, initial_target_ratio=0.05):
    """
    Initialize dynamic fee algorithm state for M market instances.

    Args:
        M: Number of market instances
        pool_config: Tuple of (linear_slope, alpha, max_fee_delta, tolerance, initial_fee, min_fee, max_fee, max_adjustment_rate)
        initial_target_ratio: Starting target ratio (should be calibrated from historical data)

    Returns:
        Tuple of state arrays and parameters
    """
    linear_slope, alpha, max_fee_delta, tolerance, initial_fee, min_fee, max_fee, max_adjustment_rate = pool_config

    # State arrays
    current_fees = np.full(M, initial_fee)
    target_ratios = np.full(M, initial_target_ratio)  # Use calibrated target
    consecutive_counters = np.zeros(M)
    last_directions = np.zeros(M)  # 0=within, 1=above, -1=below

    # EMA history tracking (simplified)
    target_ratio_history = np.full(M, initial_target_ratio)

    return (current_fees, target_ratios, consecutive_counters, last_directions,
            target_ratio_history, linear_slope, alpha, max_fee_delta, tolerance,
            min_fee, max_fee, max_adjustment_rate)


@njit
def update_target_ratio_ema(current_ratio, target_ratios, alpha, market_idx):
    """
    Update target ratio using EMA for a single market instance.
    """
    target_ratios[market_idx] = alpha * current_ratio + (1 - alpha) * target_ratios[market_idx]


@njit
def update_consecutive_counter(current_ratio, target_ratios, consecutive_counters,
                              last_directions, tolerance, market_idx):
    """
    Update consecutive out-of-range counter.
    Tolerance band is ±tolerance around the TARGET ratio.
    """
    tolerance_range = target_ratios[market_idx] * tolerance
    lower_bound = target_ratios[market_idx] - tolerance_range
    upper_bound = target_ratios[market_idx] + tolerance_range

    if current_ratio < lower_bound:
        current_direction = -1  # below
    elif current_ratio > upper_bound:
        current_direction = 1   # above
    else:
        current_direction = 0   # within

    # Update consecutive counter - CORRECTED LOGIC
    if current_ratio < lower_bound or current_ratio > upper_bound:
        # We are out of bounds
        if current_direction == last_directions[market_idx]:
            # Same direction as last time, increment counter
            consecutive_counters[market_idx] += 1
        else:
            # Different direction, reset to 1
            consecutive_counters[market_idx] = 1
    else:
        # Within tolerance bounds, reset to 0
        consecutive_counters[market_idx] = 0

    last_directions[market_idx] = current_direction


@njit
def calculate_fee_adjustment(current_ratio, current_fees, target_ratios,
                           consecutive_counters, linear_slope, max_fee_delta,
                           min_fee, max_fee, max_adjustment_rate, market_idx):
    """
    Calculate new fee for a single market instance - CORRECTED VERSION matching original algorithm.
    """
    # Step 1: Calculate deviation
    deviation = abs(current_ratio - target_ratios[market_idx])

    # Step 2: Calculate adjustment rate
    if target_ratios[market_idx] == 0:
        adjustment_rate = 0.0
    else:
        adjustment_rate = (deviation * linear_slope) / target_ratios[market_idx]

    # Bound adjustment rate
    adjustment_rate = min(adjustment_rate, max_adjustment_rate)

    # Step 3: Calculate fee delta
    fee_delta = current_fees[market_idx] * adjustment_rate

    # Step 4: Calculate step bounds with consecutive multiplier (CRITICAL CORRECTION)
    direction_multiplier = 2.0 if current_ratio < target_ratios[market_idx] else 1.0
    step_bounds = max_fee_delta * consecutive_counters[market_idx] * direction_multiplier

    # Step 5: Convert step bounds from hundredths-bp to decimal (CRITICAL CORRECTION)
    step_bounds_decimal = step_bounds / 1000000  # hundredths-bp to decimal

    # Step 6: Bound the fee delta (CRITICAL: this limits how much the fee can change per step)
    bounded_fee_delta = min(fee_delta, step_bounds_decimal)

    # Step 7: Apply adjustment
    if current_ratio > target_ratios[market_idx]:
        new_fee = current_fees[market_idx] + bounded_fee_delta
    else:
        new_fee = current_fees[market_idx] - bounded_fee_delta

    # Step 8: Apply min/max bounds
    new_fee = max(min(new_fee, max_fee), min_fee)

    return new_fee


@njit
def update_dynamic_fees_daily(daily_volumes, daily_tvls, state_arrays):
    """
    Update dynamic fees for all market instances based on daily ratios.

    Args:
        daily_volumes: Array of daily volumes
        daily_tvls: Array of daily TVLs
        state_arrays: Tuple of all state arrays and parameters

    Returns:
        Updated current_fees array
    """
    (current_fees, target_ratios, consecutive_counters, last_directions,
     target_ratio_history, linear_slope, alpha, max_fee_delta, tolerance,
     min_fee, max_fee, max_adjustment_rate) = state_arrays

    M = len(current_fees)

    for j in range(M):
        if daily_tvls[j] > 0:
            current_ratio = daily_volumes[j] / daily_tvls[j]

            # Update consecutive counter (using current target)
            update_consecutive_counter(current_ratio, target_ratios, consecutive_counters,
                                     last_directions, tolerance, j)

            # Calculate new fee (using current target) - CORRECTED with all parameters
            new_fee = calculate_fee_adjustment(current_ratio, current_fees, target_ratios,
                                             consecutive_counters, linear_slope, max_fee_delta,
                                             min_fee, max_fee, max_adjustment_rate, j)
            current_fees[j] = new_fee

            # Update target ratio for next period
            update_target_ratio_ema(current_ratio, target_ratios, alpha, j)

    return current_fees


def calculate_dynamic_fee(volume: float, tvl: float, current_fee: float,
                          target_ratio: float, consecutive_counter: int,
                          last_direction: int, params: dict) -> Tuple[float, float, int, int]:
    """
    Single-instance dynamic fee calculation (non-jit version for flexibility).

    Args:
        volume: Trading volume (USD)
        tvl: Total value locked (USD)
        current_fee: Current fee rate
        target_ratio: Current target volume/TVL ratio
        consecutive_counter: Number of consecutive periods out of tolerance
        last_direction: Previous direction (-1=below, 0=within, 1=above)
        params: Dictionary with algorithm parameters:
            - linear_slope: Adjustment sensitivity
            - alpha: EMA smoothing for target ratio
            - max_fee_delta: Max change per step (hundredths of bp)
            - tolerance: Tolerance band around target
            - min_fee: Minimum fee
            - max_fee: Maximum fee
            - max_adjustment_rate: Max relative change

    Returns:
        Tuple of (new_fee, new_target_ratio, new_consecutive_counter, new_direction)
    """
    # Extract parameters
    linear_slope = params.get('linear_slope', 0.5)
    alpha = params.get('alpha', 0.1)
    max_fee_delta = params.get('max_fee_delta', 10.0)
    tolerance = params.get('tolerance', 0.05)
    min_fee = params.get('min_fee', 0.0001)
    max_fee = params.get('max_fee', 0.01)
    max_adjustment_rate = params.get('max_adjustment_rate', 0.1)

    # Calculate current ratio
    current_ratio = volume / tvl if tvl > 0 else 0.0

    # Update consecutive counter
    tolerance_range = target_ratio * tolerance
    lower_bound = target_ratio - tolerance_range
    upper_bound = target_ratio + tolerance_range

    if current_ratio < lower_bound:
        current_direction = -1
    elif current_ratio > upper_bound:
        current_direction = 1
    else:
        current_direction = 0

    # Update consecutive counter
    if current_ratio < lower_bound or current_ratio > upper_bound:
        if current_direction == last_direction:
            new_consecutive_counter = consecutive_counter + 1
        else:
            new_consecutive_counter = 1
    else:
        new_consecutive_counter = 0

    # Calculate fee adjustment
    deviation = abs(current_ratio - target_ratio)

    if target_ratio == 0:
        adjustment_rate = 0.0
    else:
        adjustment_rate = (deviation * linear_slope) / target_ratio

    adjustment_rate = min(adjustment_rate, max_adjustment_rate)

    # Calculate fee delta
    fee_delta = current_fee * adjustment_rate

    # Apply consecutive counter multiplier
    direction_multiplier = 2.0 if current_ratio < target_ratio else 1.0
    step_bounds = max_fee_delta * new_consecutive_counter * direction_multiplier

    # Convert from hundredths-bp to decimal
    step_bounds_decimal = step_bounds / 1000000

    # Bound the fee delta
    bounded_fee_delta = min(fee_delta, step_bounds_decimal)

    # Apply adjustment
    if current_ratio > target_ratio:
        new_fee = current_fee + bounded_fee_delta
    else:
        new_fee = current_fee - bounded_fee_delta

    # Apply min/max bounds
    new_fee = max(min(new_fee, max_fee), min_fee)

    # Update target ratio with EMA
    new_target_ratio = alpha * current_ratio + (1 - alpha) * target_ratio

    return new_fee, new_target_ratio, new_consecutive_counter, current_direction