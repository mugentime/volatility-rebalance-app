#!/usr/bin/env python3
"""
Binance Volatility Strategy Web Application
Main Flask application entry point
"""

import os
import logging
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import check_password_hash, generate_password_hash
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# Import custom modules
from backend.services.binance_client import BinanceClient
from backend.services.strategy_engine import StrategyEngine
from backend.models.database import db, User, Portfolio, Transaction
from backend.routes.api_routes import api_bp
from backend.utils.auth import auth_required
from config.settings import Config

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
CORS(app)
jwt = JWTManager(app)

# Register blueprints
app.register_blueprint(api_bp, url_prefix='/api')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize strategy engine
strategy_engine = StrategyEngine()

# Background scheduler for automation
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=strategy_engine.run_automation_cycle,
    trigger="interval",
    minutes=5,
    id='strategy_automation'
)

@app.route('/')
def index():
    """Serve the main dashboard"""
    return render_template('dashboard.html')

@app.route('/healthz')
def health_check():
    """Health check endpoint for Railway"""
    return jsonify({"status": "healthy", "timestamp": str(datetime.utcnow())})

@app.route('/api/auth/login', methods=['POST'])
def login():
    """User authentication endpoint"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password_hash, password):
        access_token = create_access_token(identity=username)
        return jsonify({
            'access_token': access_token,
            'user_id': user.id
        }), 200

    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/api/portfolio/status')
@jwt_required()
def portfolio_status():
    """Get current portfolio status"""
    user_id = get_jwt_identity()
    portfolio = Portfolio.query.filter_by(user_id=user_id).first()

    if not portfolio:
        return jsonify({'error': 'Portfolio not found'}), 404

    return jsonify({
        'total_value': float(portfolio.total_value),
        'eth_balance': float(portfolio.eth_balance),
        'sol_balance': float(portfolio.sol_balance),
        'current_ltv': float(portfolio.current_ltv),
        'status': portfolio.status,
        'last_updated': portfolio.last_updated.isoformat()
    })

@app.before_first_request
def create_tables():
    """Create database tables"""
    db.create_all()

if __name__ == '__main__':
    # Start the scheduler
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())

    # Run the app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
