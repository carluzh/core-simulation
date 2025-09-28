# Core Components

This folder contains the foundational building blocks for AMM simulations. These are pure implementations without simulation logic.

## Structure

### `amm_pool.py`
- **Purpose**: Constant Product AMM implementation
- **Key Classes**:
  - `AMMPool`: Pool with x*y=k mechanics, trade execution, slippage calculation
- **Key Functions**:
  - `execute_trade()`: Execute trade with proper slippage
  - `get_best_execution()`: Find best pool for a trade
  - `get_all_quotes()`: Get quotes from multiple pools

### `dynamic_fee_engine.py`
- **Purpose**: Production dynamic fee algorithm
- **Key Functions**:
  - `initialize_dynamic_fee_state()`: Initialize algorithm state
  - `update_dynamic_fees_daily()`: Daily fee updates based on volume/TVL
  - `calculate_fee_adjustment()`: Core fee adjustment logic
- **Parameters**: 8 tunable parameters (linear_slope, alpha, max_fee_delta, etc.)

### `cpmm_engine.py`
- **Purpose**: Low-level CPMM calculations and arbitrage
- **Key Functions**:
  - `generate_cex_price()`: Generate price series
  - `arb_trade_single()`: Calculate arbitrage volumes
  - `run_daily_trading()`: Execute daily trading simulation

### `trader_agents.py`
- **Purpose**: Trader behavior modeling
- **Key Classes**:
  - `TraderAgent`: Base trader with routing logic
  - `TraderProfile`: Configuration for trader behavior
- **Trader Types**: Arbitrageur, Retail, Whale, Algorithmic, Noise
- **Key Features**:
  - Trade size generation
  - Execution evaluation
  - Pool selection logic

### `lp_actors.py`
- **Purpose**: LP behavior modeling
- **Key Classes**:
  - `LPPreferences`: LP decision parameters
  - `PoolState`: Current pool metrics
- **LP Types**: Passive, Active, Algorithmic
- **Key Features**:
  - Capital allocation decisions
  - Risk tolerance modeling
  - Rebalancing logic

## Usage

These components are imported by simulations:

```python
from core.amm_pool import AMMPool, get_all_quotes
from core.dynamic_fee_engine import initialize_dynamic_fee_state
from core.trader_agents import create_trader_population
```

## Design Principles

1. **No simulation logic** - Pure implementations only
2. **Modular** - Each component is independent
3. **Reusable** - Can be used in any simulation
4. **Production-ready** - Especially `dynamic_fee_engine.py`