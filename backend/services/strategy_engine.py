"""
ETH-SOL Volatility Strategy Engine
Handles automated portfolio management, LTV monitoring, and risk management
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from backend.services.binance_client import BinanceClient
from backend.models.database import db, Portfolio, Transaction, User
from backend.utils.calculations import calculate_ltv, calculate_optimal_allocation
from backend.utils.notifications import send_alert

logger = logging.getLogger(__name__)

class StrategyEngine:
    """Main strategy automation engine"""

    # Strategy parameters
    TARGET_LTV_MIN = 0.55  # 55% minimum LTV
    TARGET_LTV_MAX = 0.65  # 65% maximum LTV
    DANGER_LTV = 0.70      # 70% danger threshold
    EMERGENCY_LTV = 0.75   # 75% emergency liquidation

    REBALANCE_THRESHOLD = 0.05  # 5% price movement triggers rebalance

    def __init__(self):
        self.binance_client = BinanceClient()
        self.is_running = False
        self.last_prices = {'ETH': 0, 'SOL': 0}

    def run_automation_cycle(self):
        """Main automation cycle - runs every 5 minutes"""
        if self.is_running:
            logger.info("Automation cycle already running, skipping...")
            return

        self.is_running = True
        logger.info("Starting automation cycle...")

        try:
            # Get all active portfolios
            active_portfolios = Portfolio.query.filter_by(status='active').all()

            for portfolio in active_portfolios:
                self._process_portfolio(portfolio)

        except Exception as e:
            logger.error(f"Error in automation cycle: {e}")
            send_alert("Strategy Engine Error", f"Automation cycle failed: {e}")
        finally:
            self.is_running = False
            logger.info("Automation cycle completed")

    def _process_portfolio(self, portfolio: Portfolio):
        """Process individual portfolio automation"""
        try:
            user = User.query.get(portfolio.user_id)
            logger.info(f"Processing portfolio for user {user.username}")

            # Update portfolio data
            self._update_portfolio_data(portfolio)

            # Check risk levels
            if portfolio.current_ltv >= self.EMERGENCY_LTV:
                self._emergency_liquidation(portfolio)
                return
            elif portfolio.current_ltv >= self.DANGER_LTV:
                self._danger_zone_management(portfolio)
                return

            # Normal operation
            self._normal_operation(portfolio)

        except Exception as e:
            logger.error(f"Error processing portfolio {portfolio.id}: {e}")

    def _update_portfolio_data(self, portfolio: Portfolio):
        """Update portfolio with latest balance and price data"""
        try:
            # Get current balances
            spot_balances = self.binance_client.get_spot_balance()
            earn_balances = self.binance_client.get_earn_balance()
            loan_data = self.binance_client.get_loan_data()

            # Get current prices
            eth_price = self.binance_client.get_symbol_price('ETHUSDT')
            sol_price = self.binance_client.get_symbol_price('SOLUSDT')

            # Update portfolio data
            portfolio.eth_balance = self._get_total_balance('ETH', spot_balances, earn_balances)
            portfolio.sol_balance = self._get_total_balance('SOL', spot_balances, earn_balances)
            portfolio.eth_price = eth_price
            portfolio.sol_price = sol_price

            # Calculate total value and LTV
            total_collateral_value = (portfolio.eth_balance * eth_price) + (portfolio.sol_balance * sol_price)
            total_borrowed_value = self._calculate_total_borrowed_value(loan_data)

            portfolio.total_value = total_collateral_value
            portfolio.current_ltv = total_borrowed_value / total_collateral_value if total_collateral_value > 0 else 0
            portfolio.last_updated = datetime.utcnow()

            db.session.commit()

            # Check for significant price movements
            self._check_price_movements(eth_price, sol_price)

        except Exception as e:
            logger.error(f"Error updating portfolio data: {e}")
            raise

    def _get_total_balance(self, asset: str, spot_balances: List, earn_balances: Dict) -> float:
        """Calculate total balance across all wallets"""
        total = 0.0

        # Spot balance
        for balance in spot_balances:
            if balance['asset'] == asset:
                total += float(balance['free']) + float(balance['locked'])

        # Earn balances
        for flexible in earn_balances.get('flexible', []):
            if flexible['asset'] == asset:
                total += float(flexible['totalAmount'])

        for locked in earn_balances.get('locked', []):
            if locked['asset'] == asset:
                total += float(locked['totalAmount'])

        return total

    def _calculate_total_borrowed_value(self, loan_data: Dict) -> float:
        """Calculate total value of borrowed assets"""
        total_borrowed = 0.0

        for loan in loan_data.get('rows', []):
            if loan['status'] == 'BORROWING':
                coin = loan['loanCoin']
                amount = float(loan['totalAmount'])

                if coin == 'ETH':
                    price = self.binance_client.get_symbol_price('ETHUSDT')
                elif coin == 'SOL':
                    price = self.binance_client.get_symbol_price('SOLUSDT')
                else:
                    continue

                total_borrowed += amount * price

        return total_borrowed

    def _check_price_movements(self, eth_price: float, sol_price: float):
        """Check for significant price movements that trigger rebalancing"""
        if self.last_prices['ETH'] == 0:
            self.last_prices['ETH'] = eth_price
            self.last_prices['SOL'] = sol_price
            return

        eth_change = abs(eth_price - self.last_prices['ETH']) / self.last_prices['ETH']
        sol_change = abs(sol_price - self.last_prices['SOL']) / self.last_prices['SOL']

        if eth_change > self.REBALANCE_THRESHOLD or sol_change > self.REBALANCE_THRESHOLD:
            logger.info(f"Significant price movement detected - ETH: {eth_change:.2%}, SOL: {sol_change:.2%}")
            self.last_prices['ETH'] = eth_price
            self.last_prices['SOL'] = sol_price

    def _normal_operation(self, portfolio: Portfolio):
        """Handle normal operation - optimize LTV and harvest rewards"""
        try:
            # Harvest matured earn positions
            self._harvest_earn_rewards(portfolio)

            # Optimize LTV if needed
            if portfolio.current_ltv < self.TARGET_LTV_MIN:
                self._increase_leverage(portfolio)
            elif portfolio.current_ltv > self.TARGET_LTV_MAX:
                self._decrease_leverage(portfolio)

            # Log transaction
            self._log_transaction(portfolio, 'NORMAL_OPERATION', 
                                f"LTV maintained at {portfolio.current_ltv:.2%}")

        except Exception as e:
            logger.error(f"Error in normal operation: {e}")

    def _danger_zone_management(self, portfolio: Portfolio):
        """Handle danger zone - reduce leverage immediately"""
        try:
            logger.warning(f"Portfolio {portfolio.id} in danger zone - LTV: {portfolio.current_ltv:.2%}")

            # Immediately reduce leverage
            self._decrease_leverage(portfolio, aggressive=True)

            # Send alert
            send_alert("Danger Zone Alert", 
                      f"Portfolio LTV at {portfolio.current_ltv:.2%} - reducing leverage")

            self._log_transaction(portfolio, 'DANGER_ZONE', 
                                f"Emergency leverage reduction - LTV: {portfolio.current_ltv:.2%}")

        except Exception as e:
            logger.error(f"Error in danger zone management: {e}")

    def _emergency_liquidation(self, portfolio: Portfolio):
        """Handle emergency liquidation"""
        try:
            logger.critical(f"Emergency liquidation for portfolio {portfolio.id} - LTV: {portfolio.current_ltv:.2%}")

            # Stop all automation
            portfolio.status = 'emergency'

            # Liquidate all positions
            self._liquidate_all_positions(portfolio)

            # Send critical alert
            send_alert("EMERGENCY LIQUIDATION", 
                      f"Portfolio liquidated - LTV exceeded {self.EMERGENCY_LTV:.2%}")

            self._log_transaction(portfolio, 'EMERGENCY_LIQUIDATION', 
                                f"Full liquidation - LTV: {portfolio.current_ltv:.2%}")

            db.session.commit()

        except Exception as e:
            logger.critical(f"Error in emergency liquidation: {e}")

    def _increase_leverage(self, portfolio: Portfolio):
        """Increase leverage by borrowing more"""
        try:
            # Calculate optimal borrowing amounts
            target_ltv = (self.TARGET_LTV_MIN + self.TARGET_LTV_MAX) / 2
            current_collateral_value = portfolio.total_value
            target_borrowed_value = current_collateral_value * target_ltv
            current_borrowed_value = current_collateral_value * portfolio.current_ltv
            additional_borrow_needed = target_borrowed_value - current_borrowed_value

            if additional_borrow_needed <= 0:
                return

            # Split borrowing between ETH and SOL
            eth_borrow_value = additional_borrow_needed * 0.5
            sol_borrow_value = additional_borrow_needed * 0.5

            eth_borrow_amount = eth_borrow_value / portfolio.eth_price
            sol_borrow_amount = sol_borrow_value / portfolio.sol_price

            # Execute borrows
            if eth_borrow_amount > 0.001:  # Minimum borrow amount
                self.binance_client.borrow_loan('ETH', eth_borrow_amount, 'SOL')
                logger.info(f"Borrowed {eth_borrow_amount:.4f} ETH against SOL collateral")

            if sol_borrow_amount > 0.001:  # Minimum borrow amount
                self.binance_client.borrow_loan('SOL', sol_borrow_amount, 'ETH')
                logger.info(f"Borrowed {sol_borrow_amount:.4f} SOL against ETH collateral")

        except Exception as e:
            logger.error(f"Error increasing leverage: {e}")

    def _decrease_leverage(self, portfolio: Portfolio, aggressive: bool = False):
        """Decrease leverage by repaying loans"""
        try:
            loans = self.binance_client.get_loan_data()

            for loan in loans.get('rows', []):
                if loan['status'] != 'BORROWING':
                    continue

                loan_coin = loan['loanCoin']
                outstanding_amount = float(loan['totalAmount'])
                order_id = loan['orderId']

                # Determine repayment amount
                if aggressive:
                    repay_amount = outstanding_amount * 0.5  # Repay 50% in danger zone
                else:
                    repay_amount = outstanding_amount * 0.2  # Repay 20% in normal operation

                # Check if we have enough balance to repay
                if loan_coin == 'ETH' and portfolio.eth_balance >= repay_amount:
                    self.binance_client.repay_loan(order_id, repay_amount)
                    logger.info(f"Repaid {repay_amount:.4f} ETH")
                elif loan_coin == 'SOL' and portfolio.sol_balance >= repay_amount:
                    self.binance_client.repay_loan(order_id, repay_amount)
                    logger.info(f"Repaid {repay_amount:.4f} SOL")

        except Exception as e:
            logger.error(f"Error decreasing leverage: {e}")

    def _harvest_earn_rewards(self, portfolio: Portfolio):
        """Harvest and reinvest earn rewards"""
        try:
            earn_balances = self.binance_client.get_earn_balance()

            # Check for matured flexible positions
            for position in earn_balances.get('flexible', []):
                asset = position['asset']
                if asset in ['ETH', 'SOL'] and float(position['totalAmount']) > 0:
                    # Check if we can redeem and reinvest
                    available_amount = float(position['freeAmount'])
                    if available_amount > 0:
                        # Redeem and immediately re-subscribe to optimize yield
                        product_id = position['productId']
                        self.binance_client.redeem_simple_earn(product_id, available_amount)
                        time.sleep(1)  # Brief pause
                        self.binance_client.subscribe_simple_earn(product_id, available_amount)
                        logger.info(f"Harvested and reinvested {available_amount:.4f} {asset}")

        except Exception as e:
            logger.error(f"Error harvesting earn rewards: {e}")

    def _liquidate_all_positions(self, portfolio: Portfolio):
        """Emergency liquidation of all positions"""
        try:
            # Redeem all earn positions
            earn_balances = self.binance_client.get_earn_balance()

            for position in earn_balances.get('flexible', []):
                if position['asset'] in ['ETH', 'SOL']:
                    amount = float(position['totalAmount'])
                    if amount > 0:
                        self.binance_client.redeem_simple_earn(position['productId'], amount)

            # Wait for redemptions to complete
            time.sleep(10)

            # Repay all loans with available balance
            loans = self.binance_client.get_loan_data()
            for loan in loans.get('rows', []):
                if loan['status'] == 'BORROWING':
                    self.binance_client.repay_loan(loan['orderId'], float(loan['totalAmount']))

        except Exception as e:
            logger.error(f"Error in emergency liquidation: {e}")

    def _log_transaction(self, portfolio: Portfolio, transaction_type: str, description: str):
        """Log transaction to database"""
        try:
            transaction = Transaction(
                user_id=portfolio.user_id,
                transaction_type=transaction_type,
                description=description,
                eth_amount=portfolio.eth_balance,
                sol_amount=portfolio.sol_balance,
                ltv_ratio=portfolio.current_ltv,
                timestamp=datetime.utcnow()
            )
            db.session.add(transaction)
            db.session.commit()

        except Exception as e:
            logger.error(f"Error logging transaction: {e}")

    def initialize_portfolio(self, user_id: int, initial_capital_usd: float) -> Dict:
        """Initialize a new portfolio with the ETH-SOL strategy"""
        try:
            logger.info(f"Initializing portfolio for user {user_id} with ${initial_capital_usd}")

            # Split capital 50/50
            eth_capital = initial_capital_usd * 0.5
            sol_capital = initial_capital_usd * 0.5

            # Get current prices
            eth_price = self.binance_client.get_symbol_price('ETHUSDT')
            sol_price = self.binance_client.get_symbol_price('SOLUSDT')

            # Calculate amounts
            eth_amount = eth_capital / eth_price
            sol_amount = sol_capital / sol_price

            # Execute spot trades
            eth_order = self.binance_client.place_spot_order('ETHUSDT', 'BUY', eth_capital)
            sol_order = self.binance_client.place_spot_order('SOLUSDT', 'BUY', sol_capital)

            # Transfer to earn wallet and subscribe
            time.sleep(2)  # Wait for orders to settle

            self.binance_client.transfer_between_wallets('ETH', eth_amount, 'spot', 'earn')
            self.binance_client.transfer_between_wallets('SOL', sol_amount, 'spot', 'earn')

            # Subscribe to earn products (Simple Earn flexible)
            # Note: Product IDs would need to be retrieved dynamically
            # self.binance_client.subscribe_simple_earn('ETH_FLEXIBLE', eth_amount)
            # self.binance_client.subscribe_simple_earn('SOL_FLEXIBLE', sol_amount)

            # Create portfolio record
            portfolio = Portfolio(
                user_id=user_id,
                eth_balance=eth_amount,
                sol_balance=sol_amount,
                eth_price=eth_price,
                sol_price=sol_price,
                total_value=initial_capital_usd,
                current_ltv=0.0,
                status='active',
                created_at=datetime.utcnow(),
                last_updated=datetime.utcnow()
            )

            db.session.add(portfolio)
            db.session.commit()

            self._log_transaction(portfolio, 'INITIALIZATION', 
                                f"Portfolio initialized with ${initial_capital_usd}")

            return {
                'success': True,
                'portfolio_id': portfolio.id,
                'eth_amount': eth_amount,
                'sol_amount': sol_amount,
                'total_value': initial_capital_usd
            }

        except Exception as e:
            logger.error(f"Error initializing portfolio: {e}")
            return {'success': False, 'error': str(e)}
