"""
LP Agent Framework for Dynamic Fee Simulation
Two types of liquidity providers: Passive and Active
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum


class LPType(Enum):
    """LP actor types with different behavior patterns"""
    PASSIVE = "passive"      # Switches pools infrequently (~90 days)
    ACTIVE = "active"        # Switches pools frequently (~7 days)


@dataclass
class LPProfile:
    """LP preference parameters for decision making"""
    lp_type: LPType
    avg_switching_days: int           # Average days between considering switches
    switching_cost_pct: float         # Cost of switching pools as percentage
    airdrop_speculation: float        # Multiplier for pool preference (1.0 = neutral)
    capital: float                    # Total capital available


@dataclass
class PoolInfo:
    """Current state of a liquidity pool (provided by simulation)"""
    pool_id: str
    apr: float  # Annual percentage rate from fees


@dataclass
class LPPosition:
    """LP position in a specific pool"""
    pool_id: str
    capital: float
    entry_day: int
    last_switch_check_day: int  # Last day we checked for switching
    next_switch_day: int  # Next scheduled day to check switching


class LPAgent:
    """Base liquidity provider agent with switching logic"""

    def __init__(self, agent_id: int, profile: LPProfile, seed: Optional[int] = None):
        self.id = agent_id
        self.profile = profile
        self.position: Optional[LPPosition] = None
        self.switches = 0
        self.total_switching_costs = 0.0

        # Set random seed for deterministic behavior
        if seed is not None:
            self.rng = np.random.RandomState(seed + agent_id)
        else:
            self.rng = np.random.RandomState()

    def should_check_switching(self, current_day: int) -> bool:
        """
        Check if it's time to evaluate switching

        Args:
            current_day: Current simulation day

        Returns:
            Whether to check for switching opportunity
        """
        if not self.position:
            return True  # Always check if no position

        # Check if we've reached the scheduled switching day
        return current_day >= self.position.next_switch_day

    def evaluate_switch(self, current_pool: PoolInfo, alternative_pools: Dict[str, PoolInfo],
                       current_day: int) -> Optional[str]:
        """
        Evaluate whether to switch pools based on APR and switching costs

        Args:
            current_pool: Current pool info
            alternative_pools: Other available pools
            current_day: Current simulation day

        Returns:
            Pool ID to switch to, or None to stay
        """
        if not self.position:
            # No position yet, pick best pool considering airdrop speculation
            best_pool_id = None
            best_score = -float('inf')

            all_pools = {**alternative_pools, current_pool.pool_id: current_pool}
            for pool_id, pool in all_pools.items():
                score = pool.apr * self.profile.airdrop_speculation
                if score > best_score:
                    best_score = score
                    best_pool_id = pool_id

            return best_pool_id

        # Calculate days until next switch check
        days_until_next_check = self.profile.avg_switching_days

        # Current APR (with airdrop speculation)
        current_apr_adjusted = current_pool.apr * self.profile.airdrop_speculation

        # Find best alternative
        best_alternative_id = None
        best_alternative_apr = current_apr_adjusted

        for pool_id, pool in alternative_pools.items():
            if pool_id == self.position.pool_id:
                continue

            adjusted_apr = pool.apr * self.profile.airdrop_speculation

            # Calculate if switching is worth it
            # Additional APR must cover switching costs over the period
            apr_difference = adjusted_apr - current_apr_adjusted

            # Convert APR difference to return over switching period
            period_return_difference = apr_difference * (days_until_next_check / 365)

            # Switch only if additional return exceeds switching cost
            if period_return_difference > self.profile.switching_cost_pct:
                if adjusted_apr > best_alternative_apr:
                    best_alternative_apr = adjusted_apr
                    best_alternative_id = pool_id

        return best_alternative_id

    def execute_switch(self, new_pool_id: str, current_day: int) -> Dict[str, float]:
        """
        Execute pool switching

        Args:
            new_pool_id: Pool to switch to
            current_day: Current simulation day

        Returns:
            Dict with 'remove_liquidity' and 'add_liquidity' amounts
        """
        liquidity_change = {}

        if self.position and self.position.pool_id != new_pool_id:
            # Remove from current pool
            liquidity_change['remove_from'] = self.position.pool_id
            liquidity_change['remove_amount'] = self.position.capital

            # Pay switching cost
            switching_cost = self.position.capital * self.profile.switching_cost_pct
            self.total_switching_costs += switching_cost
            self.switches += 1

            # Add to new pool (minus switching cost)
            remaining_capital = self.position.capital - switching_cost
            liquidity_change['add_to'] = new_pool_id
            liquidity_change['add_amount'] = remaining_capital

            # Update position
            self.position.capital = remaining_capital
            self.position.pool_id = new_pool_id
            self.position.entry_day = current_day

        elif not self.position:
            # Initial position
            liquidity_change['add_to'] = new_pool_id
            liquidity_change['add_amount'] = self.profile.capital

            self.position = LPPosition(
                pool_id=new_pool_id,
                capital=self.profile.capital,
                entry_day=current_day,
                last_switch_check_day=current_day,
                next_switch_day=current_day
            )

        # Schedule next switching check with randomness
        if self.position:
            # Add noise: +/- 20% of average switching days
            noise_factor = self.rng.uniform(0.8, 1.2)
            days_until_next = int(self.profile.avg_switching_days * noise_factor)
            days_until_next = max(1, days_until_next)  # At least 1 day

            self.position.last_switch_check_day = current_day
            self.position.next_switch_day = current_day + days_until_next

        return liquidity_change

    def update_position_value(self, pool_apr: float, days_passed: int):
        """
        Update position value based on earned fees

        Args:
            pool_apr: Current pool APR
            days_passed: Days since last update
        """
        if self.position:
            daily_return = pool_apr / 365
            self.position.capital *= (1 + daily_return * days_passed)


class PassiveLP(LPAgent):
    """Set-and-forget liquidity provider with infrequent switching"""

    def __init__(self, agent_id: int, capital: float, seed: Optional[int] = None):
        profile = LPProfile(
            lp_type=LPType.PASSIVE,
            avg_switching_days=90,  # Check every ~90 days
            switching_cost_pct=0.005,  # 0.5% switching cost
            airdrop_speculation=1.0,  # Neutral on airdrops
            capital=capital
        )
        super().__init__(agent_id, profile, seed)


class ActiveLP(LPAgent):
    """Active liquidity provider with frequent switching"""

    def __init__(self, agent_id: int, capital: float, seed: Optional[int] = None):
        profile = LPProfile(
            lp_type=LPType.ACTIVE,
            avg_switching_days=7,  # Check every ~7 days
            switching_cost_pct=0.001,  # 0.1% switching cost
            airdrop_speculation=1.2,  # 20% bonus for potential airdrops
            capital=capital
        )
        super().__init__(agent_id, profile, seed)


def create_lp_population(distribution: Dict[str, int], capital_per_lp: float = 100_000,
                        seed: Optional[int] = None) -> list:
    """
    Create a population of LP agents

    Args:
        distribution: Dict mapping LP types to counts
                     e.g., {'passive': 50, 'active': 20}
        capital_per_lp: Capital for each LP
        seed: Random seed for deterministic behavior

    Returns:
        List of LP agents
    """
    lps = []

    for lp_type, count in distribution.items():
        for i in range(count):
            agent_id = len(lps)

            if lp_type == 'passive':
                lp = PassiveLP(agent_id, capital_per_lp, seed)
            elif lp_type == 'active':
                lp = ActiveLP(agent_id, capital_per_lp, seed)
            else:
                raise ValueError(f"Unknown LP type: {lp_type}")

            lps.append(lp)

    return lps