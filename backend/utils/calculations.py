"""
Financial calculations and portfolio metrics
"""

import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

def calculate_ltv(collateral_value: float, borrowed_value: float) -> float:
    """Calculate Loan-to-Value ratio"""
    if collateral_value <= 0:
        return 0.0
    return borrowed_value / collateral_value

def calculate_optimal_allocation(eth_price: float, sol_price: float, target_ratio: float = 0.5) -> Tuple[float, float]:
    """Calculate optimal ETH/SOL allocation weights"""
    # Simple 50/50 split for now, can be enhanced with volatility weighting
    return target_ratio, 1 - target_ratio

def calculate_portfolio_metrics(portfolio) -> Dict:
    """Calculate comprehensive portfolio metrics"""
    try:
        current_time = datetime.utcnow()

        # Basic portfolio value
        eth_value = float(portfolio.eth_balance) * float(portfolio.eth_price)
        sol_value = float(portfolio.sol_balance) * float(portfolio.sol_price)
        total_value = eth_value + sol_value

        # Asset allocation percentages
        eth_allocation = (eth_value / total_value * 100) if total_value > 0 else 0
        sol_allocation = (sol_value / total_value * 100) if total_value > 0 else 0

        # Risk metrics
        ltv_utilization = (float(portfolio.current_ltv) / 0.65 * 100) if portfolio.current_ltv else 0

        # Safety buffer
        safety_buffer = max(0, 0.65 - float(portfolio.current_ltv)) * total_value if portfolio.current_ltv else 0

        return {
            'total_value_usd': round(total_value, 2),
            'eth_value_usd': round(eth_value, 2),
            'sol_value_usd': round(sol_value, 2),
            'eth_allocation_pct': round(eth_allocation, 1),
            'sol_allocation_pct': round(sol_allocation, 1),
            'ltv_utilization_pct': round(ltv_utilization, 1),
            'safety_buffer_usd': round(safety_buffer, 2),
            'risk_level': get_risk_level(float(portfolio.current_ltv) if portfolio.current_ltv else 0)
        }

    except Exception as e:
        return {
            'total_value_usd': 0,
            'eth_value_usd': 0,
            'sol_value_usd': 0,
            'eth_allocation_pct': 0,
            'sol_allocation_pct': 0,
            'ltv_utilization_pct': 0,
            'safety_buffer_usd': 0,
            'risk_level': 'UNKNOWN'
        }

def get_risk_level(ltv: float) -> str:
    """Determine risk level based on LTV"""
    if ltv < 0.45:
        return 'LOW'
    elif ltv < 0.60:
        return 'MEDIUM'
    elif ltv < 0.70:
        return 'HIGH'
    else:
        return 'CRITICAL'

def calculate_rebalance_amounts(current_eth: float, current_sol: float, 
                              eth_price: float, sol_price: float,
                              target_allocation: float = 0.5) -> Dict:
    """Calculate amounts needed for rebalancing"""

    current_total_value = (current_eth * eth_price) + (current_sol * sol_price)
    target_eth_value = current_total_value * target_allocation
    target_sol_value = current_total_value * (1 - target_allocation)

    current_eth_value = current_eth * eth_price
    current_sol_value = current_sol * sol_price

    eth_diff_value = target_eth_value - current_eth_value
    sol_diff_value = target_sol_value - current_sol_value

    return {
        'eth_rebalance_amount': eth_diff_value / eth_price,
        'sol_rebalance_amount': sol_diff_value / sol_price,
        'eth_action': 'BUY' if eth_diff_value > 0 else 'SELL',
        'sol_action': 'BUY' if sol_diff_value > 0 else 'SELL',
        'rebalance_needed': abs(eth_diff_value) > (current_total_value * 0.05)  # 5% threshold
    }

def calculate_volatility(prices: List[float], period_days: int = 30) -> float:
    """Calculate annualized volatility from price series"""
    if len(prices) < 2:
        return 0.0

    returns = np.diff(np.log(prices))
    daily_vol = np.std(returns)
    annualized_vol = daily_vol * np.sqrt(365)

    return float(annualized_vol)

def estimate_yield_projection(current_balance: float, apr: float, days: int) -> Dict:
    """Estimate yield projection for earn products"""
    daily_rate = apr / 365
    projected_yield = current_balance * daily_rate * days
    compound_yield = current_balance * ((1 + daily_rate) ** days - 1)

    return {
        'simple_yield': round(projected_yield, 6),
        'compound_yield': round(compound_yield, 6),
        'final_balance': round(current_balance + compound_yield, 6)
    }
