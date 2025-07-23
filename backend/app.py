import os
import sys
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from flask_httpauth import HTTPBasicAuth
from apscheduler.schedulers.background import BackgroundScheduler
import logging
from datetime import datetime
import atexit

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use absolute imports instead of relative imports
from backend.services.binance_client import BinanceClient
from backend.services.strategy_engine import StrategyEngine  
from backend.models.database import db, User, Transaction

app = Flask(__name__)
CORS(app)
auth = HTTPBasicAuth()

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///binance_strategy.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Initialize services
binance_client = BinanceClient()
strategy_engine = StrategyEngine(binance_client)

# Authentication
@auth.verify_password
def authenticate(username, password):
    return (username == os.getenv('BASIC_AUTH_USERNAME', 'admin') and 
            password == os.getenv('BASIC_AUTH_PASSWORD', 'password'))

# Background scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=strategy_engine.run_strategy_cycle,
    trigger="interval",
    minutes=int(os.getenv('SCHEDULER_INTERVAL', 5)),
    id='strategy_cycle'
)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

@app.route('/')
@auth.login_required
def dashboard():
    return render_template_string(open('frontend/index.html').read())

@app.route('/api/portfolio')
@auth.login_required
def get_portfolio():
    try:
        portfolio = binance_client.get_portfolio_summary()
        return jsonify(portfolio)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ltv')
@auth.login_required
def get_ltv():
    try:
        ltv_data = strategy_engine.calculate_current_ltv()
        return jsonify(ltv_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/start_strategy', methods=['POST'])
@auth.login_required
def start_strategy():
    try:
        result = strategy_engine.initialize_strategy()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop_strategy', methods=['POST'])
@auth.login_required
def stop_strategy():
    try:
        result = strategy_engine.emergency_unwind()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions')
@auth.login_required
def get_transactions():
    try:
        transactions = Transaction.query.order_by(Transaction.timestamp.desc()).limit(50).all()
        return jsonify([{
            'id': t.id,
            'type': t.transaction_type,
            'asset': t.asset,
            'amount': float(t.amount),
            'timestamp': t.timestamp.isoformat(),
            'status': t.status
        } for t in transactions])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
