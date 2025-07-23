"""
Binance API Client for ETH-SOL Volatility Strategy
Handles all Binance API interactions with proper authentication and error handling
"""

import hashlib
import hmac
import time
import requests
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode
import os

logger = logging.getLogger(__name__)

class BinanceClient:
    """Secure Binance API client with HMAC authentication"""

    BASE_URL = "https://api.binance.com"

    def __init__(self):
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.api_secret = os.getenv('BINANCE_API_SECRET')

        if not self.api_key or not self.api_secret:
            raise ValueError("Binance API credentials not found in environment variables")

    def _generate_signature(self, query_string: str) -> str:
        """Generate HMAC SHA256 signature for Binance API"""
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _make_request(self, method: str, endpoint: str, params: Dict = None, signed: bool = False) -> Dict:
        """Make authenticated request to Binance API"""
        url = f"{self.BASE_URL}{endpoint}"

        headers = {
            'X-MBX-APIKEY': self.api_key,
            'Content-Type': 'application/json'
        }

        if params is None:
            params = {}

        if signed:
            params['timestamp'] = int(time.time() * 1000)
            query_string = urlencode(params)
            params['signature'] = self._generate_signature(query_string)

        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=params, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Binance API request failed: {e}")
            raise

    def get_account_info(self) -> Dict:
        """Get account information"""
        return self._make_request('GET', '/api/v3/account', signed=True)

    def get_spot_balance(self) -> List[Dict]:
        """Get spot wallet balances"""
        account_info = self.get_account_info()
        return [balance for balance in account_info['balances'] if float(balance['free']) > 0]

    def get_funding_balance(self) -> List[Dict]:
        """Get funding wallet balances"""
        return self._make_request('POST', '/sapi/v1/asset/get-funding-asset', signed=True)

    def get_earn_balance(self) -> Dict:
        """Get Simple Earn balances"""
        flexible = self._make_request('GET', '/sapi/v1/simple-earn/flexible/position', signed=True)
        locked = self._make_request('GET', '/sapi/v1/simple-earn/locked/position', signed=True)

        return {
            'flexible': flexible.get('rows', []),
            'locked': locked.get('rows', [])
        }

    def place_spot_order(self, symbol: str, side: str, quantity: float, order_type: str = 'MARKET') -> Dict:
        """Place a spot order"""
        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': quantity
        }

        if order_type == 'MARKET':
            params['quoteOrderQty'] = quantity
            del params['quantity']

        return self._make_request('POST', '/api/v3/order', params, signed=True)

    def get_symbol_price(self, symbol: str) -> float:
        """Get current price for a symbol"""
        params = {'symbol': symbol}
        response = self._make_request('GET', '/api/v3/ticker/price', params)
        return float(response['price'])

    def subscribe_simple_earn(self, product_id: str, amount: float) -> Dict:
        """Subscribe to Simple Earn flexible product"""
        params = {
            'productId': product_id,
            'amount': amount
        }
        return self._make_request('POST', '/sapi/v1/simple-earn/flexible/subscribe', params, signed=True)

    def redeem_simple_earn(self, product_id: str, amount: float) -> Dict:
        """Redeem from Simple Earn flexible product"""
        params = {
            'productId': product_id,
            'amount': amount,
            'type': 'FAST'
        }
        return self._make_request('POST', '/sapi/v1/simple-earn/flexible/redeem', params, signed=True)

    def get_loan_data(self) -> Dict:
        """Get current loan information"""
        return self._make_request('GET', '/sapi/v1/loan/ongoing/orders', signed=True)

    def borrow_loan(self, coin: str, amount: float, collateral_coin: str) -> Dict:
        """Borrow against collateral"""
        params = {
            'loanCoin': coin,
            'loanAmount': amount,
            'collateralCoin': collateral_coin
        }
        return self._make_request('POST', '/sapi/v1/loan/borrow', params, signed=True)

    def repay_loan(self, order_id: str, amount: float) -> Dict:
        """Repay loan"""
        params = {
            'orderId': order_id,
            'amount': amount
        }
        return self._make_request('POST', '/sapi/v1/loan/repay', params, signed=True)

    def transfer_between_wallets(self, asset: str, amount: float, from_wallet: str, to_wallet: str) -> Dict:
        """Transfer assets between wallets"""
        # Wallet type mapping
        wallet_types = {
            'spot': 'MAIN',
            'funding': 'FUNDING',
            'earn': 'EARN'
        }

        params = {
            'asset': asset,
            'amount': amount,
            'fromWallet': wallet_types.get(from_wallet, from_wallet),
            'toWallet': wallet_types.get(to_wallet, to_wallet)
        }
        return self._make_request('POST', '/sapi/v1/asset/transfer', params, signed=True)
