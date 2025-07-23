"""
API Routes for the Binance Volatility Strategy application
RESTful endpoints for frontend interaction
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from datetime import datetime, timedelta
import logging

from backend.models.database import db, User, Portfolio, Transaction, EarnPosition, LoanPosition, SystemAlert
from backend.services.strategy_engine import StrategyEngine
from backend.utils.auth import validate_api_credentials
from backend.utils.calculations import calculate_portfolio_metrics

logger = logging.getLogger(__name__)
api_bp = Blueprint('api', __name__)

# Initialize strategy engine
strategy_engine = StrategyEngine()

@api_bp.route('/auth/login', methods=['POST'])
def login():
    """Authenticate user and return JWT token"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            access_token = create_access_token(
                identity=user.id,
                expires_delta=timedelta(hours=24)
            )

            # Update last login
            user.last_login = datetime.utcnow()
            db.session.commit()

            return jsonify({
                'access_token': access_token,
                'user_id': user.id,
                'username': user.username
            }), 200

        return jsonify({'error': 'Invalid credentials'}), 401

    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@api_bp.route('/auth/register', methods=['POST'])
def register():
    """Register new user"""
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not all([username, email, password]):
            return jsonify({'error': 'All fields required'}), 400

        # Check if user exists
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already exists'}), 400

        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        return jsonify({'message': 'User created successfully'}), 201

    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'error': 'Registration failed'}), 500

@api_bp.route('/portfolio/status', methods=['GET'])
@jwt_required()
def get_portfolio_status():
    """Get current portfolio status"""
    try:
        user_id = get_jwt_identity()
        portfolio = Portfolio.query.filter_by(user_id=user_id).first()

        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404

        # Calculate real-time metrics
        metrics = calculate_portfolio_metrics(portfolio)

        return jsonify({
            'portfolio_id': portfolio.id,
            'eth_balance': float(portfolio.eth_balance),
            'sol_balance': float(portfolio.sol_balance),
            'eth_price': float(portfolio.eth_price),
            'sol_price': float(portfolio.sol_price),
            'total_value': float(portfolio.total_value),
            'current_ltv': float(portfolio.current_ltv),
            'target_ltv_min': float(portfolio.target_ltv_min),
            'target_ltv_max': float(portfolio.target_ltv_max),
            'status': portfolio.status,
            'auto_rebalance': portfolio.auto_rebalance,
            'total_profit_loss': float(portfolio.total_profit_loss),
            'last_updated': portfolio.last_updated.isoformat(),
            'metrics': metrics
        }), 200

    except Exception as e:
        logger.error(f"Portfolio status error: {e}")
        return jsonify({'error': 'Failed to get portfolio status'}), 500

@api_bp.route('/portfolio/initialize', methods=['POST'])
@jwt_required()
def initialize_portfolio():
    """Initialize new portfolio with ETH-SOL strategy"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        initial_capital = data.get('initial_capital_usd')

        if not initial_capital or initial_capital <= 0:
            return jsonify({'error': 'Valid initial capital required'}), 400

        # Check if portfolio already exists
        existing_portfolio = Portfolio.query.filter_by(user_id=user_id).first()
        if existing_portfolio:
            return jsonify({'error': 'Portfolio already exists'}), 400

        # Initialize portfolio using strategy engine
        result = strategy_engine.initialize_portfolio(user_id, initial_capital)

        if result['success']:
            return jsonify({
                'message': 'Portfolio initialized successfully',
                'portfolio_id': result['portfolio_id'],
                'eth_amount': result['eth_amount'],
                'sol_amount': result['sol_amount'],
                'total_value': result['total_value']
            }), 201
        else:
            return jsonify({'error': result['error']}), 500

    except Exception as e:
        logger.error(f"Portfolio initialization error: {e}")
        return jsonify({'error': 'Failed to initialize portfolio'}), 500

@api_bp.route('/portfolio/start', methods=['POST'])
@jwt_required()
def start_automation():
    """Start portfolio automation"""
    try:
        user_id = get_jwt_identity()
        portfolio = Portfolio.query.filter_by(user_id=user_id).first()

        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404

        portfolio.status = 'active'
        portfolio.auto_rebalance = True
        db.session.commit()

        return jsonify({'message': 'Automation started'}), 200

    except Exception as e:
        logger.error(f"Start automation error: {e}")
        return jsonify({'error': 'Failed to start automation'}), 500

@api_bp.route('/portfolio/stop', methods=['POST'])
@jwt_required()
def stop_automation():
    """Stop portfolio automation"""
    try:
        user_id = get_jwt_identity()
        portfolio = Portfolio.query.filter_by(user_id=user_id).first()

        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404

        portfolio.status = 'paused'
        portfolio.auto_rebalance = False
        db.session.commit()

        return jsonify({'message': 'Automation stopped'}), 200

    except Exception as e:
        logger.error(f"Stop automation error: {e}")
        return jsonify({'error': 'Failed to stop automation'}), 500

@api_bp.route('/portfolio/emergency-stop', methods=['POST'])
@jwt_required()
def emergency_stop():
    """Emergency stop and liquidation"""
    try:
        user_id = get_jwt_identity()
        portfolio = Portfolio.query.filter_by(user_id=user_id).first()

        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404

        # Trigger emergency liquidation
        strategy_engine._emergency_liquidation(portfolio)

        return jsonify({'message': 'Emergency stop executed'}), 200

    except Exception as e:
        logger.error(f"Emergency stop error: {e}")
        return jsonify({'error': 'Failed to execute emergency stop'}), 500

@api_bp.route('/transactions', methods=['GET'])
@jwt_required()
def get_transactions():
    """Get transaction history"""
    try:
        user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        transactions = Transaction.query.filter_by(user_id=user_id)\
                         .order_by(Transaction.timestamp.desc())\
                         .paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'transactions': [{
                'id': tx.id,
                'type': tx.transaction_type,
                'description': tx.description,
                'eth_amount': float(tx.eth_amount) if tx.eth_amount else 0,
                'sol_amount': float(tx.sol_amount) if tx.sol_amount else 0,
                'usd_value': float(tx.usd_value) if tx.usd_value else 0,
                'ltv_ratio': float(tx.ltv_ratio) if tx.ltv_ratio else 0,
                'timestamp': tx.timestamp.isoformat()
            } for tx in transactions.items],
            'pagination': {
                'page': transactions.page,
                'pages': transactions.pages,
                'per_page': transactions.per_page,
                'total': transactions.total
            }
        }), 200

    except Exception as e:
        logger.error(f"Get transactions error: {e}")
        return jsonify({'error': 'Failed to get transactions'}), 500

@api_bp.route('/earn-positions', methods=['GET'])
@jwt_required()
def get_earn_positions():
    """Get current earn positions"""
    try:
        user_id = get_jwt_identity()
        positions = EarnPosition.query.filter_by(user_id=user_id)\
                      .filter(EarnPosition.status.in_(['ACTIVE', 'MATURED']))\
                      .all()

        return jsonify({
            'positions': [{
                'id': pos.id,
                'asset': pos.asset,
                'product_type': pos.product_type,
                'principal_amount': float(pos.principal_amount),
                'current_amount': float(pos.current_amount),
                'rewards_earned': float(pos.rewards_earned),
                'apr': float(pos.apr) if pos.apr else 0,
                'status': pos.status,
                'subscription_time': pos.subscription_time.isoformat()
            } for pos in positions]
        }), 200

    except Exception as e:
        logger.error(f"Get earn positions error: {e}")
        return jsonify({'error': 'Failed to get earn positions'}), 500

@api_bp.route('/loan-positions', methods=['GET'])
@jwt_required()
def get_loan_positions():
    """Get current loan positions"""
    try:
        user_id = get_jwt_identity()
        positions = LoanPosition.query.filter_by(user_id=user_id)\
                      .filter_by(status='BORROWING')\
                      .all()

        return jsonify({
            'positions': [{
                'id': pos.id,
                'loan_coin': pos.loan_coin,
                'collateral_coin': pos.collateral_coin,
                'loan_amount': float(pos.loan_amount),
                'outstanding_amount': float(pos.outstanding_amount),
                'interest_rate': float(pos.interest_rate) if pos.interest_rate else 0,
                'ltv_ratio': float(pos.ltv_ratio),
                'borrow_time': pos.borrow_time.isoformat()
            } for pos in positions]
        }), 200

    except Exception as e:
        logger.error(f"Get loan positions error: {e}")
        return jsonify({'error': 'Failed to get loan positions'}), 500

@api_bp.route('/alerts', methods=['GET'])
@jwt_required()
def get_alerts():
    """Get system alerts"""
    try:
        user_id = get_jwt_identity()
        alerts = SystemAlert.query.filter_by(user_id=user_id)\
                   .order_by(SystemAlert.created_at.desc())\
                   .limit(50).all()

        return jsonify({
            'alerts': [{
                'id': alert.id,
                'type': alert.alert_type,
                'severity': alert.severity,
                'title': alert.title,
                'message': alert.message,
                'is_read': alert.is_read,
                'created_at': alert.created_at.isoformat()
            } for alert in alerts]
        }), 200

    except Exception as e:
        logger.error(f"Get alerts error: {e}")
        return jsonify({'error': 'Failed to get alerts'}), 500

@api_bp.route('/alerts/<int:alert_id>/read', methods=['POST'])
@jwt_required()
def mark_alert_read(alert_id):
    """Mark alert as read"""
    try:
        user_id = get_jwt_identity()
        alert = SystemAlert.query.filter_by(id=alert_id, user_id=user_id).first()

        if not alert:
            return jsonify({'error': 'Alert not found'}), 404

        alert.is_read = True
        db.session.commit()

        return jsonify({'message': 'Alert marked as read'}), 200

    except Exception as e:
        logger.error(f"Mark alert read error: {e}")
        return jsonify({'error': 'Failed to mark alert as read'}), 500

@api_bp.route('/settings/ltv', methods=['POST'])
@jwt_required()
def update_ltv_settings():
    """Update LTV target settings"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        target_ltv_min = data.get('target_ltv_min')
        target_ltv_max = data.get('target_ltv_max')

        if not all([target_ltv_min, target_ltv_max]):
            return jsonify({'error': 'Both LTV targets required'}), 400

        if target_ltv_min >= target_ltv_max or target_ltv_max > 0.70:
            return jsonify({'error': 'Invalid LTV range'}), 400

        portfolio = Portfolio.query.filter_by(user_id=user_id).first()
        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404

        portfolio.target_ltv_min = target_ltv_min
        portfolio.target_ltv_max = target_ltv_max
        db.session.commit()

        return jsonify({'message': 'LTV settings updated'}), 200

    except Exception as e:
        logger.error(f"Update LTV settings error: {e}")
        return jsonify({'error': 'Failed to update LTV settings'}), 500

@api_bp.route('/manual/rebalance', methods=['POST'])
@jwt_required()
def manual_rebalance():
    """Trigger manual rebalance"""
    try:
        user_id = get_jwt_identity()
        portfolio = Portfolio.query.filter_by(user_id=user_id).first()

        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404

        # Process portfolio with strategy engine
        strategy_engine._process_portfolio(portfolio)

        return jsonify({'message': 'Manual rebalance completed'}), 200

    except Exception as e:
        logger.error(f"Manual rebalance error: {e}")
        return jsonify({'error': 'Failed to execute manual rebalance'}), 500
