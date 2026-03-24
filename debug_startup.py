from flask import Flask, render_template, request, flash, redirect, url_for, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import joblib
import numpy as np
import os
import logging
from datetime import datetime, timedelta
import uuid
import json
from collections import deque
from utils.preprocess import validate_input_data, create_features
from utils.auth import (generate_token, decode_token, login_rate_limiter,
                        get_client_ip, get_user_agent, role_required, admin_required)
from models.user import User, user_store

print("DEBUG: Configuring logging...")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
print("DEBUG: Logging configured.")
logger = logging.getLogger(__name__)

print("DEBUG: Initializing Flask app...")
app = Flask(__name__)
print("DEBUG: Flask app initialized.")
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(32).hex())
print("DEBUG: Secret key set.")

print("DEBUG: Initializing LoginManager...")
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'
print("DEBUG: LoginManager initialized.")

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return user_store.get_user_by_id(user_id)

# Load trained model and encoders
MODEL_DIR = "model"
try:
    print("DEBUG: Mocking model loading...")
    class MockModel:
        def predict(self, X): return [0]
        def predict_proba(self, X): return [[0.9, 0.1]]
        def load_model(self, path): pass
    model = MockModel()
    label_encoders = {}
    threshold = 0.5
    print("DEBUG: Model mocked. Encoders and threshold set.")
    logger.info("Encoders and threshold mocked successfully")
except Exception as e:
    print(f"DEBUG: Error mocking model: {e}")
    logger.error(f"Error mocking model: {str(e)}")
    model = None
    label_encoders = None
    threshold = 0.5

# Enhanced in-memory statistics with timestamps and history
stats = {
    'total_predictions': 0,
    'fraud_detected': 0,
    'legitimate_transactions': 0,
    'total_amount_analyzed': 0.0,
    'fraud_amount_blocked': 0.0,
    'start_time': datetime.now(),
    'last_prediction_time': None,
    'hourly_predictions': deque(maxlen=24),  # Last 24 hours
    'recent_transactions': deque(maxlen=100),  # Last 100 transactions
    'risk_distribution': {'Very Low': 0, 'Low': 0, 'Medium': 0, 'High': 0, 'Very High': 0},
    'category_stats': {},
    'avg_response_times': deque(maxlen=100)
}

# Track system uptime
system_start_time = datetime.now()

@app.route('/')
@login_required
def home():
    fraud_rate = (stats['fraud_detected'] / stats['total_predictions'] * 100) if stats['total_predictions'] > 0 else 0

    # Calculate uptime
    uptime_delta = datetime.now() - system_start_time
    uptime_hours = uptime_delta.total_seconds() / 3600
    uptime_days = uptime_delta.days

    # Calculate average response time
    avg_response = sum(stats['avg_response_times']) / len(stats['avg_response_times']) if stats['avg_response_times'] else 0.25

    # Calculate amount-based statistics
    total_amount = stats.get('total_amount_analyzed', 0)
    fraud_amount = stats.get('fraud_amount_blocked', 0)
    avg_transaction_amount = total_amount / stats['total_predictions'] if stats['total_predictions'] > 0 else 0

    dashboard_data = {
        'total_predictions': stats['total_predictions'],
        'fraud_detected': stats['fraud_detected'],
        'legitimate_transactions': stats['legitimate_transactions'],
        'fraud_rate': round(fraud_rate, 2),
        'avg_processing_time': round(avg_response * 1000, 2),  # Convert to ms
        'uptime_hours': round(uptime_hours, 1),
        'uptime_days': uptime_days,
        'model_status': 'Active' if model is not None else 'Not Loaded',
        'model_accuracy': 99.7,
        'last_training': 'N/A',
        'total_amount_analyzed': round(total_amount, 2),
        'fraud_amount_blocked': round(fraud_amount, 2),
        'avg_transaction_amount': round(avg_transaction_amount, 2),
        'risk_distribution': stats['risk_distribution'],
        'recent_transactions': list(stats['recent_transactions'])[-10:],  # Last 10
        'last_prediction_time': stats.get('last_prediction_time'),
    }

    return render_template("home.html", dashboard_data=dashboard_data)

# ... (omitting remaining routes for brevity, assuming they are same as app_no_model.py)
# Actually, I should probably copy the whole thing or just the important parts.
# I'll just write a very minimal app to see if Flask even starts.

if __name__ == '__main__':
    print("DEBUG: Entering main block...")
    debug_mode = False
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '127.0.0.1')

    print(f"DEBUG: Starting server on {host}:{port} with debug={debug_mode}")
    app.run(host=host, port=port, debug=debug_mode)
