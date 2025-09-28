# Adaptive Fee Optimization

A Python library for simulating adaptive fee optimization in automated market makers (AMMs). This library implements dynamic fee mechanisms that automatically adjust based on market conditions to provide temporal market segmentation between different user types.

## Overview

This library provides:

- **Core AMM Engine**: Constant product market maker implementation with realistic mechanics
- **Dynamic Fee Algorithm**: Adaptive fee optimization that adjusts based on volume/TVL ratios
- **Agent-Based Models**: Trader and liquidity provider behavior simulation
- **Market Data Integration**: Support for real market data analysis
- **Comprehensive Testing**: Mathematical validation and robustness analysis

## Key Features

### Dynamic Fee Optimization
- Automatically adjusts fees based on recent volume/TVL ratios
- Provides temporal market segmentation for different trader types
- Supports multiple pool configurations (stable, standard, volatile pairs)
- Configurable parameters for different market conditions

### Agent-Based Simulation
- **Trader Agents**: Arbitrageurs, retail traders, and whale traders
- **LP Agents**: Passive and active liquidity providers with switching behavior
- **Realistic Behavior**: Based on actual market participant patterns

### Mathematical Foundation
- Proven convergence and stability properties
- Comprehensive parameter sensitivity analysis
- Robust to realistic market conditions

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd adaptive-fee-optimization

# Install dependencies
pip install -r requirements.txt
```

## Project Structure

```
├── core/                    # Core library components
│   ├── amm_pool.py         # AMM pool implementation
│   ├── dynamic_fee_engine.py  # Dynamic fee algorithm
│   ├── trader_agents.py    # Trading agent models
│   ├── lp_agents.py        # Liquidity provider models
│   ├── cex_arbitrage.py    # CEX-AMM arbitrage calculations
│   └── README.md           # Core module documentation
├── Data/                   # Market data and test datasets
│   └── Risky/             # Historical trading data
├── config.py              # Configuration parameters
└── README.md             # This file
```

## Quick Start

```python
from core.amm_pool import AMMPool
from core.dynamic_fee_engine import calculate_dynamic_fee
from core.trader_agents import create_trader_population

# Create pools
static_pool = AMMPool("static", fee=0.003, reserve_x=100, reserve_y=3_000_000)
dynamic_pool = AMMPool("dynamic", fee=0.003, reserve_x=10, reserve_y=300_000)

# Create trader population
traders = create_trader_population({
    'arbitrageur': 3,
    'retail': 50,
    'whale': 2
})

# Calculate dynamic fee adjustment
new_fee, target_ratio = calculate_dynamic_fee(
    volume=1000000,    # $1M daily volume
    tvl=50000000,      # $50M TVL
    current_fee=0.003, # Current 0.3% fee
    # ... other parameters
)
```

## Configuration

The library supports multiple pool configurations optimized for different market conditions:

```python
from config import POOL_CONFIGS

# Standard pair (ETH/USDC)
standard_config = POOL_CONFIGS['standard']

# Volatile pair (MEME/ETH)
volatile_config = POOL_CONFIGS['volatile']

# Stable pair (USDC/USDT)
stable_config = POOL_CONFIGS['stable']
```

## Data

The library includes historical market data for:
- ETH/USDC pairs at 0.05%, 0.3%, and 1.0% fee tiers
- WBTC/USDC pairs at 0.05% and 0.3% fee tiers

## Mathematical Validation

The dynamic fee algorithm has been validated for:
- **Convergence**: Reaches stable equilibrium under constant conditions
- **Stability**: Robust to market volatility and parameter changes
- **Economic Logic**: Properly responds to volume and TVL changes
- **Parameter Sensitivity**: Well-characterized response to configuration changes

## License

This project is provided for research and educational purposes. See individual files for specific licensing terms.

## Citation

If you use this library in your research, please cite:

```
@software{adaptive_fee_optimization,
  title={Adaptive Fee Optimization for AMMs},
  author={Your Name},
  year={2025},
  url={https://github.com/your-repo/adaptive-fee-optimization}
}
```
