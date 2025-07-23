"""
Database models for the Binance Volatility Strategy application
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    """User model for authentication and profile management"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    binance_api_key = db.Column(db.Text, nullable=True)  # Encrypted
    binance_api_secret = db.Column(db.Text, nullable=True)  # Encrypted
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
    portfolios = db.relationship('Portfolio', backref='user', lazy=True)
    transactions = db.relationship('Transaction', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Portfolio(db.Model):
    """Portfolio model to track user's ETH-SOL strategy positions"""
    __tablename__ = 'portfolios'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Asset balances
    eth_balance = db.Column(db.Numeric(20, 8), default=0.0)
    sol_balance = db.Column(db.Numeric(20, 8), default=0.0)

    # Current prices (for LTV calculation)
    eth_price = db.Column(db.Numeric(20, 8), default=0.0)
    sol_price = db.Column(db.Numeric(20, 8), default=0.0)

    # Portfolio metrics
    total_value = db.Column(db.Numeric(20, 2), default=0.0)
    current_ltv = db.Column(db.Numeric(5, 4), default=0.0)  # Loan-to-Value ratio

    # Strategy settings
    target_ltv_min = db.Column(db.Numeric(5, 4), default=0.55)
    target_ltv_max = db.Column(db.Numeric(5, 4), default=0.65)
    auto_rebalance = db.Column(db.Boolean, default=True)

    # Status tracking
    status = db.Column(db.String(20), default='active')  # active, paused, emergency, liquidated
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    last_rebalance = db.Column(db.DateTime)

    # Performance tracking
    total_profit_loss = db.Column(db.Numeric(20, 2), default=0.0)
    total_yield_earned = db.Column(db.Numeric(20, 8), default=0.0)

    def __repr__(self):
        return f'<Portfolio {self.id} - User {self.user_id}>'

class Transaction(db.Model):
    """Transaction log for all portfolio activities"""
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Transaction details
    transaction_type = db.Column(db.String(50), nullable=False)  # BUY, SELL, BORROW, REPAY, EARN_SUBSCRIBE, etc.
    description = db.Column(db.Text)

    # Asset amounts involved
    eth_amount = db.Column(db.Numeric(20, 8), default=0.0)
    sol_amount = db.Column(db.Numeric(20, 8), default=0.0)
    usd_value = db.Column(db.Numeric(20, 2), default=0.0)

    # Trading details
    symbol = db.Column(db.String(20))
    side = db.Column(db.String(10))  # BUY, SELL
    price = db.Column(db.Numeric(20, 8))
    fees = db.Column(db.Numeric(20, 8), default=0.0)

    # Portfolio state at time of transaction
    ltv_ratio = db.Column(db.Numeric(5, 4))
    total_portfolio_value = db.Column(db.Numeric(20, 2))

    # External references
    binance_order_id = db.Column(db.String(100))
    binance_tx_id = db.Column(db.String(100))

    # Timestamps
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Transaction {self.id} - {self.transaction_type}>'

class EarnPosition(db.Model):
    """Track Simple Earn and staking positions"""
    __tablename__ = 'earn_positions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Position details
    asset = db.Column(db.String(10), nullable=False)
    product_type = db.Column(db.String(20), nullable=False)  # FLEXIBLE, LOCKED, STAKING
    product_id = db.Column(db.String(50), nullable=False)

    # Amounts
    principal_amount = db.Column(db.Numeric(20, 8), nullable=False)
    current_amount = db.Column(db.Numeric(20, 8), nullable=False)
    rewards_earned = db.Column(db.Numeric(20, 8), default=0.0)

    # Rates and terms
    apr = db.Column(db.Numeric(8, 6))  # Annual Percentage Rate
    lock_period = db.Column(db.Integer)  # Days for locked products

    # Status
    status = db.Column(db.String(20), default='ACTIVE')  # ACTIVE, MATURED, REDEEMED
    subscription_time = db.Column(db.DateTime, default=datetime.utcnow)
    maturity_time = db.Column(db.DateTime)
    redemption_time = db.Column(db.DateTime)

    # External references
    binance_position_id = db.Column(db.String(100))

    def __repr__(self):
        return f'<EarnPosition {self.id} - {self.asset} {self.product_type}>'

class LoanPosition(db.Model):
    """Track loan positions and collateral"""
    __tablename__ = 'loan_positions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Loan details
    loan_coin = db.Column(db.String(10), nullable=False)
    collateral_coin = db.Column(db.String(10), nullable=False)

    # Amounts
    loan_amount = db.Column(db.Numeric(20, 8), nullable=False)
    collateral_amount = db.Column(db.Numeric(20, 8), nullable=False)
    outstanding_amount = db.Column(db.Numeric(20, 8), nullable=False)

    # Rates and LTV
    interest_rate = db.Column(db.Numeric(8, 6))
    ltv_ratio = db.Column(db.Numeric(5, 4))
    liquidation_ltv = db.Column(db.Numeric(5, 4))

    # Status
    status = db.Column(db.String(20), default='BORROWING')  # BORROWING, REPAID, LIQUIDATED
    borrow_time = db.Column(db.DateTime, default=datetime.utcnow)
    repay_time = db.Column(db.DateTime)

    # External references
    binance_order_id = db.Column(db.String(100))

    def __repr__(self):
        return f'<LoanPosition {self.id} - {self.loan_coin}/{self.collateral_coin}>'

class SystemAlert(db.Model):
    """System alerts and notifications"""
    __tablename__ = 'system_alerts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Alert details
    alert_type = db.Column(db.String(50), nullable=False)  # LTV_WARNING, LIQUIDATION, ERROR, etc.
    severity = db.Column(db.String(20), default='INFO')  # INFO, WARNING, ERROR, CRITICAL
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)

    # Status
    is_read = db.Column(db.Boolean, default=False)
    is_resolved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)

    def __repr__(self):
        return f'<SystemAlert {self.id} - {self.alert_type}>'
