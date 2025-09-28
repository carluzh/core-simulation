"""
Configuration parameters for dynamic fee simulation
Centralizes all simulation parameters and data paths
"""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent
CPMM_DATA_DIR = BASE_DIR.parent / "cpmm-trading" / "data"
WORKING_PAPER_DATA_DIR = BASE_DIR.parent / "Working Paper" / "Data"
RESULTS_DIR = BASE_DIR / "results"

# Ensure results directory exists
RESULTS_DIR.mkdir(exist_ok=True)

# Simulation parameters
class SimulationConfig:
    """Default simulation parameters"""
    
    # Market instances and time
    M = 100  # Market instances for statistical significance
    N = 252  # Trading days (1 year)
    T = 1.0  # Time horizon (1 year)
    
    # Price dynamics
    S_INITIAL = 2000.0  # Initial ETH price
    MU = 0.05          # 5% annual drift
    SIGMA = 0.8        # 80% annualized volatility
    
    # Trading parameters - FLAT $200K DAILY VOLUME
    BUY_AMT = 100000.0   # $100k systematic buy orders  
    SELL_AMT = -100000.0 # $100k systematic sell orders (total = $200k/day)
    ETA0 = 0.001         # 0.1% CEX trading cost
    
    # Pool initialization - REALISTIC SCALE
    X0 = 1000000         # $1M initial dollar reserves
    Y0 = 500             # 500 ETH initial asset reserves
    
    # Fee parameters
    STATIC_FEE = 0.0005  # 0.05% baseline static fee
    
    @property
    def dt(self):
        return self.T / self.N
    
    @property
    def initial_tvl(self):
        return self.X0 + self.Y0 * self.S_INITIAL

# Pool type configurations
POOL_CONFIGS = {
    'stable': {
        'code': 0,
        'linear_slope': 0.5,
        'alpha': 0.1,
        'max_fee_delta': 50,
        'tolerance': 0.02,
        'initial_fee': 0.0001,  # 0.01%
        'min_fee': 0.00005,     # 0.005% 
        'max_fee': 0.01,        # 1%
        'max_adjustment_rate': 100.0,
        'description': 'Stable pairs (USDC/USDT)'
    },
    'standard': {
        'code': 1,
        'linear_slope': 1.0,
        'alpha': 0.15,
        'max_fee_delta': 100,
        'tolerance': 0.05,     # 5% tolerance - RESET to original
        'initial_fee': 0.0005,  # 0.05% - CORRECT starting fee
        'min_fee': 0.0001,     # 0.01% - minimum fee bound
        'max_fee': 0.03,       # 3% - maximum fee bound
        'max_adjustment_rate': 100.0,
        'description': 'Standard pairs (ETH/USDC)'
    },
    'volatile': {
        'code': 2,
        'linear_slope': 2.0,
        'alpha': 0.2,
        'max_fee_delta': 200,
        'tolerance': 0.05,
        'initial_fee': 0.003,   # 0.3%
        'min_fee': 0.0005,      # 0.05%
        'max_fee': 0.05,        # 5%
        'max_adjustment_rate': 100.0,
        'description': 'Volatile pairs (MEME/ETH)'
    }
}

# Data paths
HISTORICAL_DATA_PATHS = {
    'eth_usdc_005': WORKING_PAPER_DATA_DIR / "Risky" / "ETH_USDC_0.05%.csv",
    'eth_usdc_03': WORKING_PAPER_DATA_DIR / "Risky" / "ETH_USDC_0.3%.csv",
    'eth_usdc_10': WORKING_PAPER_DATA_DIR / "Risky" / "ETH_USDC_1.0%.csv",
    'wbtc_usdc_005': WORKING_PAPER_DATA_DIR / "Risky" / "WBTC_USDC_0.05%.csv",
    'wbtc_usdc_03': WORKING_PAPER_DATA_DIR / "Risky" / "WBTC_USDC_0.3%.csv",
}

# CPMM trading simulation results
CPMM_RESULT_PATTERNS = {
    'low_volume': "all_outputs_eta0_*_mu_0.0_buy_250_sell_250.pkl",
    'medium_volume': "all_outputs_eta0_*_mu_0.0_buy_2500_sell_2500.pkl", 
    'high_volume': "all_outputs_eta0_*_mu_0.0_buy_25000_sell_25000.pkl"
}
