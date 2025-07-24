import os
import sys
import logging
from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
from flask_httpauth import HTTPBasicAuth
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import atexit

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our modules
from backend.services.binance_client import BinanceClient
from backend.services.strategy_engine import StrategyEngine
  
from backend.models.database import db, User, Transaction, StrategyState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins=["*"])
auth = HTTPBasicAuth()

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///binance_strategy.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

# Initialize database
db.init_app(app)

# Global variables for services
binance_client = None
strategy_engine = None
scheduler = None

# Authentication
@auth.verify_password
def authenticate(username, password):
    expected_username = os.getenv('BASIC_AUTH_USERNAME', 'admin')
    expected_password = os.getenv('BASIC_AUTH_PASSWORD', 'password')
    return username == expected_username and password == expected_password

@auth.error_handler
def auth_error(status):
    return jsonify({'error': 'Authentication required'}), 401

# Initialize services function
def initialize_services():
    global binance_client, strategy_engine, scheduler
    
    try:
        # Initialize Binance client
        binance_client = BinanceClient()
        logger.info("Binance client initialized successfully")
        
        # Initialize strategy engine
        strategy_engine = StrategyEngine(binance_client)
        logger.info("Strategy engine initialized successfully")
        
        # Initialize background scheduler
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            func=run_strategy_cycle,
            trigger="interval",
            minutes=int(os.getenv('SCHEDULER_INTERVAL', 5)),
            id='strategy_cycle'
        )
        scheduler.start()
        logger.info("Background scheduler started")
        
        # Register shutdown handler
        atexit.register(lambda: scheduler.shutdown() if scheduler else None)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        return False

def run_strategy_cycle():
    """Wrapper function for strategy cycle to handle errors"""
    try:
        if strategy_engine:
            strategy_engine.run_strategy_cycle()
    except Exception as e:
        logger.error(f"Strategy cycle error: {e}")

# Routes
@app.route('/')
@auth.login_required
def dashboard():
    """Serve the main dashboard"""
    try:
        # Try to serve the frontend HTML file
        frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'index.html')
        if os.path.exists(frontend_path):
            with open(frontend_path, 'r') as f:
                return f.read()
        else:
            # Fallback HTML if frontend file doesn't exist
            return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Binance Volatility Strategy</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    .container { max-width: 1200px; margin: 0 auto; }
                    .card { background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 8px; }
                    .status { padding: 10px; border-radius: 4px; margin: 10px 0; }
                    .status.success { background: #d4edda; color: #155724; }
                    .status.error { background: #f8d7da; color: #721c24; }
                    button { padding: 10px 20px; margin: 5px; border: none; border-radius: 4px; cursor: pointer; }
                    .btn-primary { background: #007bff; color: white; }
                    .btn-danger { background: #dc3545; color: white; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Binance Volatility Strategy Dashboard</h1>
                    <div class="card">
                        <h2>Strategy Status</h2>
                        <div id="status">Loading...</div>
                        <button class="btn-primary" onclick="startStrategy()">Start Strategy</button>
                        <button class="btn-danger" onclick="stopStrategy()">Stop Strategy</button>
                    </div>
                    <div class="card">
                        <h2>Portfolio Overview</h2>
                        <div id="portfolio">Loading...</div>
                    </div>
                    <div class="card">
                        <h2>LTV Status</h2>
                        <div id="ltv">Loading...</div>
                    </div>
                </div>
                
                <script>
                    function makeAuthenticatedRequest(url, options = {}) {
                        const auth = btoa('{{ auth.username() }}:{{ request.authorization.password }}');
                        return fetch(url, {
                            ...options,
                            headers: {
                                ...options.headers,
                                'Authorization': 'Basic ' + auth,
                                'Content-Type': 'application/json'
                            }
                        });
                    }
                    
                    function updateStatus() {
                        makeAuthenticatedRequest('/api/ltv')
                            .then(response => response.json())
                            .then(data => {
                                document.getElementById('ltv').innerHTML = 
                                    `<p>Current LTV: ${(data.current_ltv * 100).toFixed(2)}%</p>
                                     <p>Collateral Value: $${data.collateral_value?.toFixed(2) || 0}</p>
                                     <p>Borrowed Value: $${data.borrowed_value?.toFixed(2) || 0}</p>`;
                            })
                            .catch(err => {
                                document.getElementById('ltv').innerHTML = '<p class="status error">Error loading LTV data</p>';
                            });
                            
                        makeAuthenticatedRequest('/api/portfolio')
                            .then(response => response.json())
                            .then(data => {
                                document.getElementById('portfolio').innerHTML = 
                                    `<p>Total Value: $${data.total_value_usd?.toFixed(2) || 0}</p>
                                     <p>ETH Price: $${data.prices?.ETH?.toFixed(2) || 0}</p>
                                     <p>SOL Price: $${data.prices?.SOL?.toFixed(2) || 0}</p>`;
                            })
                            .catch(err => {
                                document.getElementById('portfolio').innerHTML = '<p class="status error">Error loading portfolio data</p>';
                            });
                    }
                    
                    function startStrategy() {
                        makeAuthenticatedRequest('/api/start_strategy', { method: 'POST' })
                            .then(response => response.json())
                            .then(data => {
                                if (data.error) {
                                    document.getElementById('status').innerHTML = `<p class="status error">${data.error}</p>`;
                                } else {
                                    document.getElementById('status').innerHTML = `<p class="status success">${data.message}</p>`;
                                }
                            });
                    }
                    
                    function stopStrategy() {
                        makeAuthenticatedRequest('/api/stop_strategy', { method: 'POST' })
                            .then(response => response.json())
                            .then(data => {
                                if (data.error) {
                                    document.getElementById('status').innerHTML = `<p class="status error">${data.error}</p>`;
                                } else {
                                    document.getElementById('status').innerHTML = `<p class="status success">${data.message}</p>`;
                                }
                            });
                    }
                    
                    // Update every 30 seconds
                    setInterval(updateStatus, 30000);
                    updateStatus();
                </script>
            </body>
            </html>
            """)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return jsonify({'error': 'Dashboard unavailable'}), 500

@app.route('/api/portfolio')
@auth.login_required
def get_portfolio():
    """Get current portfolio summary"""
    try:
        if not binance_client:
            return jsonify({'error': 'Binance client not initialized'}), 500
            
        portfolio = binance_client.get_portfolio_summary()
        return jsonify(portfolio)
    except Exception as e:
        logger.error(f"Portfolio API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ltv')
@auth.login_required
def get_ltv():
    """Get current LTV status"""
    try:
        if not strategy_engine:
            return jsonify({'error': 'Strategy engine not initialized'}), 500
            
        ltv_data = strategy_engine.calculate_current_ltv()
        return jsonify(ltv_data)
    except Exception as e:
        logger.error(f"LTV API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/start_strategy', methods=['POST'])
@auth.login_required
def start_strategy():
    """Start the automated strategy"""
    try:
        if not strategy_engine:
            return jsonify({'error': 'Strategy engine not initialized'}), 500
            
        result = strategy_engine.initialize_strategy()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Start strategy error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop_strategy', methods=['POST'])
@auth.login_required
def stop_strategy():
    """Stop the automated strategy"""
    try:
        if not strategy_engine:
            return jsonify({'error': 'Strategy engine not initialized'}), 500
            
        result = strategy_engine.emergency_unwind()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Stop strategy error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions')
@auth.login_required
def get_transactions():
    """Get recent transactions"""
    try:
        transactions = Transaction.query.order_by(Transaction.timestamp.desc()).limit(50).all()
        return jsonify([{
            'id': t.id,
            'type': t.transaction_type,
            'asset': t.asset,
            'amount': str(t.amount),  # Convert to string to avoid JSON serialization issues
            'price': str(t.price) if t.price else None,
            'timestamp': t.timestamp.isoformat() if t.timestamp else None,
            'status': t.status
        } for t in transactions])
    except Exception as e:
        logger.error(f"Transactions API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/strategy_state')
@auth.login_required
def get_strategy_state():
    """Get current strategy state"""
    try:
        state = StrategyState.query.first()
        if not state:
            return jsonify({
                'is_running': False,
                'current_ltv': 0,
                'total_collateral_value': 0,
                'total_borrowed_value': 0
            })
        
        return jsonify({
            'is_running': state.is_running,
            'current_ltv': float(state.current_ltv) if state.current_ltv else 0,
            'total_collateral_value': float(state.total_collateral_value) if state.total_collateral_value else 0,
            'total_borrowed_value': float(state.total_borrowed_value) if state.total_borrowed_value else 0,
            'last_rebalance': state.last_rebalance.isoformat() if state.last_rebalance else None
        })
    except Exception as e:
        logger.error(f"Strategy state API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Health check endpoint for Railway"""
    try:
        # Check database connection
        with app.app_context():
            db.session.execute('SELECT 1')
        
        # Check if services are initialized
        services_status = {
            'binance_client': binance_client is not None,
            'strategy_engine': strategy_engine is not None,
            'scheduler': scheduler is not None and scheduler.running
        }
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'services': services_status
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/api/test_connection')
@auth.login_required
def test_binance_connection():
    """Test Binance API connection"""
    try:
        if not binance_client:
            return jsonify({'error': 'Binance client not initialized'}), 500
            
        # Test connection by getting account info
        account = binance_client.get_account_info()
        return jsonify({
            'status': 'connected',
            'account_type': account.get('accountType', 'Unknown'),
            'can_trade': account.get('canTrade', False),
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Binance connection test failed: {e}")
        return jsonify({'error': str(e), 'status': 'disconnected'}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

# Application initialization
def create_app():
    """Application factory function"""
    with app.app_context():
        try:
            # Create database tables
            db.create_all()
            logger.info("Database tables created successfully")
            
            # Initialize services
            if initialize_services():
                logger.info("All services initialized successfully")
            else:
                logger.warning("Some services failed to initialize")
                
        except Exception as e:
            logger.error(f"Application initialization error: {e}")
    
    return app

# Main execution
if __name__ == '__main__':
    # Create the application
    app = create_app()
    
    # Get port from environment
    port = int(os.getenv('PORT', 8080))
    
    # Run the application
    logger.info(f"Starting Binance Volatility Strategy App on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
