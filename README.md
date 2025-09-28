# Core AMM Simulation Components

A collection of foundational components for building AMM simulations with dynamic fee optimization. Provides core building blocks for constant product market makers, fee adjustment algorithms, and agent-based trading behavior.

## Overview

This repository contains modular components for AMM simulation:

- **AMM Pool Engine**: Basic constant product market maker implementation
- **Alphix Dynamic Fee Algorithm**: Prototype fee adjustment based on volume/TVL ratios
- **Agent Models**: Basic trader and liquidity provider behavior frameworks
- **Arbitrage Logic**: CEX-AMM arbitrage calculation utilities

## Current Components

### AMM Pool Engine
- Basic constant product market maker (x*y=k)
- Trade execution with slippage calculation
- Liquidity management functions

### Dynamic Fee Algorithm
- Volume/TVL ratio-based fee adjustment
- EMA smoothing for target ratios
- Consecutive counter for stability

### Agent Frameworks
- **Trader Agents**: Basic trader types (arbitrageur, retail, whale) with trade size generation
- **LP Agents**: Basic LP types (passive, active) with pool switching and APR-based decisions

### Arbitrage Utilities
- **CEXArbitrageur**: Sophisticated CEX-AMM arbitrage with optimal trade sizing
- **ArbitrageOpportunity**: Detailed arbitrage opportunity tracking
- Fee-aware calculations and execution capabilities

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd core-simulation

# Install dependencies (numpy, numba)
pip install numpy numba
```

## Project Structure

```
├── core/                    # Core library components
│   ├── amm_pool.py         # AMM pool implementation
│   ├── dynamic_fee_engine.py  # Dynamic fee algorithm
│   ├── trader_agents.py    # Trading agent models
│   ├── lp_agents.py        # Liquidity provider models
│   ├── cex_arbitrage.py    # CEX-AMM arbitrage calculations
│   └── __init__.py         # Module exports
├── Data/                   # Market data
│   └── Risky/             # Historical trading data (ETH/USDC, WBTC/USDC)
├── config.py              # Configuration parameters
└── README.md             # This file
```

## Quick Start

```python
from core import AMMPool, calculate_dynamic_fee, create_trader_population, get_pool_config, create_pool_config_tuple

# Create pools
static_pool = AMMPool("static", fee=0.0005, reserve_x=500, reserve_y=1_000_000)
dynamic_pool = AMMPool("dynamic", fee=0.0005, reserve_x=500, reserve_y=1_000_000)

# Create trader population
traders = create_trader_population({
    'arbitrageur': 3,
    'retail': 50,
    'whale': 2
})

# Get configuration for standard pool type
config = get_pool_config('standard')
pool_config_tuple = create_pool_config_tuple(config)

# Calculate dynamic fee adjustment using config
new_fee, target_ratio, counter, direction = calculate_dynamic_fee(
    volume=200000,     # $200k daily volume
    tvl=2000000,       # $2M TVL
    current_fee=config['initial_fee'],
    target_ratio=0.1,  # Target volume/TVL ratio
    consecutive_counter=0,
    last_direction=0,
    params=config      # Use config dict directly
)
```

## Configuration

The library supports multiple pool configurations:

```python
from core import POOL_CONFIGS, get_pool_config, create_pool_config_tuple

# Direct access to all configs
configs = POOL_CONFIGS

# Get configuration for specific pool type
standard_config = get_pool_config('standard')
volatile_config = get_pool_config('volatile')
stable_config = get_pool_config('stable')

# Convert to format expected by dynamic fee engine
pool_config_tuple = create_pool_config_tuple(standard_config)

# Use config parameters directly
new_fee, target_ratio, counter, direction = calculate_dynamic_fee(
    volume=200000,
    tvl=2000000,
    current_fee=standard_config['initial_fee'],
    target_ratio=0.1,
    consecutive_counter=0,
    last_direction=0,
    params=standard_config  # Pass config dict directly
)

# Available configuration parameters:
# - linear_slope: Fee adjustment sensitivity
# - alpha: EMA smoothing factor for target ratio
# - max_fee_delta: Maximum fee change per step
# - tolerance: Tolerance band around target ratio
# - initial_fee, min_fee, max_fee: Fee bounds
# - max_adjustment_rate: Maximum relative fee change

## Multi-Pool Operations

For scenarios with multiple AMM pools, utility functions are available:

```python
from core import get_all_quotes, get_best_execution

# Get quotes from multiple pools
pools = [pool1, pool2, pool3]
quotes = get_all_quotes(pools, trade_size=1000, is_buy=True)
# Returns: {'pool1': {...}, 'pool2': {...}, 'pool3': {...}}

# Find best execution across pools
best_pool, best_result = get_best_execution(pools, trade_size=1000, is_buy=True)
# Returns: (best_pool, execution_details_dict)

## Arbitrage Features

Sophisticated CEX-AMM arbitrage capabilities:

```python
from core import CEXArbitrageur, calculate_arbitrage_volume

# Create arbitrageur with custom parameters
arb = CEXArbitrageur(cex_fee=0.001, max_capital=100_000)

# Calculate arbitrage opportunity
opportunity = arb.calculate_arbitrage(pool, cex_price=2000)

# Execute arbitrage if profitable
executed, opportunity = arb.execute_arbitrage(pool, cex_price=2000, min_profit=0.01)

# Quick calculation function
arb_details = calculate_arbitrage_volume(pool, cex_price=2000, cex_fee=0.001)
# Returns: {'direction', 'eth_volume', 'usd_volume', 'profit', ...}

## LP Agent Features

Liquidity provider behavior modeling:

```python
from core import create_lp_population, LPAgent, LPProfile

# Create LP population with different strategies
lps = create_lp_population({
    'passive': 50,   # Set-and-forget LPs
    'active': 20     # Frequent switchers
}, capital_per_lp=100_000)

# Individual LP management
lp_profile = LPProfile(
    lp_type='active',
    avg_switching_days=7,
    switching_cost_pct=0.001,
    airdrop_speculation=1.2,
    capital=100_000
)

lp_agent = LPAgent(agent_id=1, profile=lp_profile)

# LP agents evaluate pool switches based on APR and costs
should_switch = lp_agent.should_check_switching(current_day=30)
if should_switch:
    new_pool = lp_agent.evaluate_switch(current_pool, alternative_pools, current_day)
    if new_pool:
        liquidity_change = lp_agent.execute_switch(new_pool, current_day)
```

## Data

Historical market data available for backtesting and analysis:
- **ETH/USDC pairs** at 0.05%, 0.3%, and 1.0% fee tiers
- **WBTC/USDC pairs** at 0.05% and 0.3% fee tiers

**Data Format**: CSV files with OHLCV data for historical analysis and parameter calibration.

**Usage**: These datasets can be used to:
- Calibrate dynamic fee parameters
- Backtest trading strategies
- Analyze market conditions for different pool types

## Implementation Status

### AMMPool ✓
- Basic constant product market maker implementation
- Trade execution with slippage calculation
- Liquidity add/remove functionality
- Multi-pool utilities: `get_best_execution()`, `get_all_quotes()`

### Dynamic Fee Engine ⚠️
- Prototype fee adjustment algorithm
- Basic EMA smoothing and counter logic
- Needs integration with full simulation framework

### Agent Models ⚠️
- Basic trader and LP agent frameworks
- Simple behavior models and switching logic
- Requires full simulation environment to be functional

### Note
These are foundational components that provide building blocks for AMM simulation. They require integration into a complete simulation framework to be fully operational.
