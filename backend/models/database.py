from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    api_key_encrypted = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_type = db.Column(db.String(50), nullable=False)  # 'buy', 'sell', 'earn_subscribe', etc.
    asset = db.Column(db.String(10), nullable=False)  # 'ETH', 'SOL', etc.
    amount = db.Column(db.String(50), nullable=False)  # Store as string to avoid Decimal issues
    price = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'completed', 'failed'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    extra_data = db.Column(db.Text, nullable=True)  # Changed from 'metadata' to 'extra_data'
    
    def __repr__(self):
        return f'<Transaction {self.transaction_type} {self.asset} {self.amount}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'transaction_type': self.transaction_type,
            'asset': self.asset,
            'amount': self.amount,
            'price': self.price,
            'status': self.status,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'extra_data': self.extra_data
        }

class StrategyState(db.Model):
    __tablename__ = 'strategy_states'
    
    id = db.Column(db.Integer, primary_key=True)
    is_running = db.Column(db.Boolean, default=False)
    current_ltv = db.Column(db.String(20), nullable=True)  # Store as string to avoid Decimal issues
    total_collateral_value = db.Column(db.String(50), nullable=True)
    total_borrowed_value = db.Column(db.String(50), nullable=True)
    last_rebalance = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<StrategyState running={self.is_running} ltv={self.current_ltv}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'is_running': self.is_running,
            'current_ltv': float(self.current_ltv) if self.current_ltv else None,
            'total_collateral_value': float(self.total_collateral_value) if self.total_collateral_value else None,
            'total_borrowed_value': float(self.total_borrowed_value) if self.total_borrowed_value else None,
            'last_rebalance': self.last_rebalance.isoformat() if self.last_rebalance else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
