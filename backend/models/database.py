from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, Text

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    api_key_encrypted = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    transaction_type = Column(String(50), nullable=False)  # 'buy', 'sell', 'earn_subscribe', etc.
    asset = Column(String(10), nullable=False)  # 'ETH', 'SOL', etc.
    amount = Column(Numeric(precision=20, scale=8), nullable=False)
    price = Column(Numeric(precision=20, scale=8), nullable=True)
    status = Column(String(20), default='pending')  # 'pending', 'completed', 'failed'
    timestamp = Column(DateTime, default=datetime.utcnow)
    metadata = Column(Text, nullable=True)  # JSON string for additional data
    
    def __repr__(self):
        return f'<Transaction {self.transaction_type} {self.asset} {self.amount}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'transaction_type': self.transaction_type,
            'asset': self.asset,
            'amount': float(self.amount),
            'price': float(self.price) if self.price else None,
            'status': self.status,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'metadata': self.metadata
        }

class StrategyState(db.Model):
    __tablename__ = 'strategy_states'
    
    id = Column(Integer, primary_key=True)
    is_running = Column(Boolean, default=False)
    current_ltv = Column(Numeric(precision=5, scale=4), nullable=True)
    total_collateral_value = Column(Numeric(precision=20, scale=2), nullable=True)
    total_borrowed_value = Column(Numeric(precision=20, scale=2), nullable=True)
    last_rebalance = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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
