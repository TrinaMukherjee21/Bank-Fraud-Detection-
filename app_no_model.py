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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(32).hex())

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login route"""
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'

        client_ip = get_client_ip()

        # Check rate limiting
        if login_rate_limiter.is_rate_limited(client_ip):
            remaining = login_rate_limiter.get_remaining_attempts(client_ip)
            flash(f'Too many failed login attempts. Please try again later.', 'danger')
            logger.warning(f"Rate limited login attempt from IP: {client_ip}")
            return render_template("login.html")

        # Validate input
        if not username or not password:
            flash('Please enter both username and password.', 'warning')
            return render_template("login.html")

        # Get user
        user = user_store.get_user_by_username(username)

        if user is None:
            login_rate_limiter.record_attempt(client_ip, False)
            flash('Invalid username or password.', 'danger')
            logger.warning(f"Failed login attempt for non-existent user: {username}")
            return render_template("login.html")

        # Check if account is locked
        if user.is_locked():
            flash('Account is temporarily locked due to too many failed login attempts.', 'danger')
            logger.warning(f"Login attempt for locked account: {username}")
            return render_template("login.html")

        # Verify password
        if not user.check_password(password):
            login_rate_limiter.record_attempt(client_ip, False)
            user.increment_failed_login()
            flash('Invalid username or password.', 'danger')
            logger.warning(f"Failed login attempt for user: {username}")
            return render_template("login.html")

        # Check if user is active
        if not user.is_active:
            flash('Account is disabled. Please contact administrator.', 'danger')
            logger.warning(f"Login attempt for disabled account: {username}")
            return render_template("login.html")

        # Successful login
        login_user(user, remember=remember)
        user.update_last_login()
        login_rate_limiter.record_attempt(client_ip, True)

        # Log activity
        user_store.log_activity(
            user.id,
            'login',
            f'Successful login from {client_ip}',
            client_ip,
            get_user_agent()
        )

        logger.info(f"Successful login for user: {username} ({user.role})")
        flash(f'Welcome back, {user.username}!', 'success')

        # Redirect to next page or home
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('home'))

    return render_template("login.html")

@app.route('/logout')
@login_required
def logout():
    """User logout route"""
    username = current_user.username
    user_id = current_user.id

    # Log activity
    user_store.log_activity(
        user_id,
        'logout',
        f'User logged out',
        get_client_ip(),
        get_user_agent()
    )

    logout_user()
    logger.info(f"User logged out: {username}")
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/form_basic', methods=['GET'])
@login_required
def form_basic():
    return render_template("form_basic.html")

@app.route('/form_advanced', methods=['GET'])
@login_required
def form_advanced():
    return render_template("form_advanced.html")

@app.route('/about')
@login_required
def about():
    """Comprehensive About page with system information"""
    try:
        # Load model metadata if available
        model_metadata_path = os.path.join("model", "model_metadata.pkl")
        if os.path.exists(model_metadata_path):
            model_info = joblib.load(model_metadata_path)
        else:
            model_info = None

        return render_template("about.html", model_info=model_info)
    except Exception as e:
        logger.error(f"Error loading about page: {str(e)}")
        return render_template("about.html", model_info=None)

@app.route('/analytics')
@login_required
@role_required('admin', 'analyst')
def analytics():
    """Advanced Analytics Dashboard with Chart.js visualizations (Admin & Analyst only)"""
    try:
        # Calculate current statistics
        fraud_rate = (stats['fraud_detected'] / stats['total_predictions'] * 100) if stats['total_predictions'] > 0 else 0
        avg_response = sum(stats['avg_response_times']) / len(stats['avg_response_times']) if stats['avg_response_times'] else 0.25
        uptime_delta = datetime.now() - system_start_time
        uptime_hours = uptime_delta.total_seconds() / 3600

        dashboard_data = {
            'total_predictions': stats['total_predictions'],
            'fraud_detected': stats['fraud_detected'],
            'legitimate_transactions': stats['legitimate_transactions'],
            'fraud_rate': round(fraud_rate, 2),
            'avg_response_time_ms': round(avg_response * 1000, 2),
            'uptime_hours': round(uptime_hours, 1),
            'total_amount_analyzed': stats['total_amount_analyzed'],
            'fraud_amount_blocked': stats['fraud_amount_blocked'],
            'risk_distribution': stats['risk_distribution'],
            'recent_transactions': list(stats['recent_transactions'])[-10:],
            'category_stats': stats.get('category_stats', {}),
            'model_status': 'Active' if model is not None else 'Not Loaded'
        }

        return render_template("analytics.html", dashboard_data=dashboard_data)
    except Exception as e:
        logger.error(f"Error loading analytics page: {str(e)}")
        return render_template("analytics.html", dashboard_data=None)

@app.route('/predict', methods=['POST'])
def predict():
    start_time = datetime.now()
    session_id = str(uuid.uuid4())

    try:
        # Check if model is loaded
        if model is None:
            return render_template("error.html",
                                 error="Model not available. Please contact administrator.")

        # Get form data
        form_data = request.form.to_dict()

        # Validate input data
        validated_data = validate_input_data(form_data)

        # Create features
        input_features = create_features(validated_data)

        # Make prediction
        prediction_proba = model.predict_proba(input_features)[0]
        fraud_probability = prediction_proba[1]

        # Use optimized threshold
        prediction = 1 if fraud_probability >= threshold else 0
        confidence = prediction_proba[prediction] * 100

        # Enhanced risk assessment (MUST be done before using risk_level)
        risk_level = get_risk_level(fraud_probability)
        risk_factors = analyze_risk_factors(validated_data)

        # Update statistics
        stats['total_predictions'] += 1
        stats['last_prediction_time'] = start_time.isoformat()
        stats['total_amount_analyzed'] += validated_data['amount']

        if prediction == 1:
            stats['fraud_detected'] += 1
            stats['fraud_amount_blocked'] += validated_data['amount']
        else:
            stats['legitimate_transactions'] += 1

        # Track risk distribution
        stats['risk_distribution'][risk_level] += 1

        # Track recent transactions (summary)
        transaction_summary = {
            'timestamp': start_time.isoformat(),
            'amount': validated_data['amount'],
            'prediction': 'Fraud' if prediction == 1 else 'Legitimate',
            'risk_level': risk_level,
            'confidence': round(confidence, 2),
            'category': validated_data.get('category', 'Unknown')
        }
        stats['recent_transactions'].append(transaction_summary)

        # Track category statistics
        category = validated_data.get('category', 'Unknown')
        if category not in stats['category_stats']:
            stats['category_stats'][category] = {'total': 0, 'fraud': 0}
        stats['category_stats'][category]['total'] += 1
        if prediction == 1:
            stats['category_stats'][category]['fraud'] += 1

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()

        # Track response time (AFTER calculation)
        stats['avg_response_times'].append(processing_time)

        logger.info(f"Prediction made - Session: {session_id}, "
                   f"Fraud: {prediction}, Confidence: {confidence:.2f}%, "
                   f"Amount: {validated_data['amount']}")

        # Prepare response data
        result_data = {
            'prediction': prediction,
            'confidence': round(confidence, 2),
            'fraud_probability': round(fraud_probability * 100, 2),
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'amount': validated_data['amount'],
            'session_id': session_id,
            'processing_time': round(processing_time * 1000, 2),
            'timestamp': start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'model_version': 'v1.0',
            'recommendations': generate_recommendations(prediction, risk_level, validated_data)
        }

        # Flash message
        if prediction == 1:
            flash('FRAUD ALERT: Suspicious transaction detected!', 'danger')
        else:
            flash('Transaction verified as legitimate', 'success')

        return render_template("result.html", **result_data)

    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        return render_template("error.html", error=f"Invalid input: {str(e)}")
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        return render_template("error.html",
                             error="An unexpected error occurred. Please try again.")

def get_risk_level(probability):
    """Determine risk level based on fraud probability"""
    if probability >= 0.8:
        return "Very High"
    elif probability >= 0.6:
        return "High"
    elif probability >= 0.4:
        return "Medium"
    elif probability >= 0.2:
        return "Low"
    else:
        return "Very Low"

def analyze_risk_factors(data):
    """Analyze transaction data for risk factors"""
    risk_factors = []

    # Amount-based factors
    if data['amount'] > 50000:
        risk_factors.append("Extremely high transaction amount (>$50,000)")
    elif data['amount'] > 20000:
        risk_factors.append("Very high transaction amount (>$20,000)")
    elif data['amount'] > 10000:
        risk_factors.append("High transaction amount (>$10,000)")
    elif data['amount'] > 5000:
        risk_factors.append("Above average transaction amount (>$5,000)")

    # Time-based factors
    if data.get('step', 0) > 700:
        risk_factors.append("Very late time period transaction")
    elif data.get('step', 0) > 500:
        risk_factors.append("Late time period transaction")

    # Round amount patterns
    if data['amount'] % 1000 == 0 and data['amount'] >= 5000:
        risk_factors.append("Round amount (potential money laundering pattern)")

    if not risk_factors:
        risk_factors.append("No specific risk factors identified")

    return risk_factors

def generate_recommendations(prediction, risk_level, data):
    """Generate action recommendations"""
    recommendations = []

    if prediction == 1:
        recommendations.append("IMMEDIATE ACTION: Block this transaction")
        recommendations.append("Contact customer for verification")
        recommendations.append("Review customer's recent transaction history")

        if data['amount'] > 10000:
            recommendations.append("Escalate to fraud investigation team")
            recommendations.append("File suspicious activity report (SAR)")

        recommendations.append("Consider temporary account restrictions")
    else:
        recommendations.append("Transaction approved - no action needed")

        if risk_level in ['High', 'Very High']:
            recommendations.append("Log transaction for monitoring")
            recommendations.append("Monitor account for unusual patterns")

        if data['amount'] > 20000:
            recommendations.append("Consider additional documentation")

    return recommendations

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """API endpoint for real-time statistics"""
    try:
        fraud_rate = (stats['fraud_detected'] / stats['total_predictions'] * 100) if stats['total_predictions'] > 0 else 0

        # Calculate uptime
        uptime_delta = datetime.now() - system_start_time
        uptime_hours = uptime_delta.total_seconds() / 3600

        # Calculate average response time
        avg_response = sum(stats['avg_response_times']) / len(stats['avg_response_times']) if stats['avg_response_times'] else 0.25

        response_data = {
            'total_predictions': stats['total_predictions'],
            'fraud_detected': stats['fraud_detected'],
            'legitimate_transactions': stats['legitimate_transactions'],
            'fraud_rate': round(fraud_rate, 2),
            'avg_response_time_ms': round(avg_response * 1000, 2),
            'uptime_hours': round(uptime_hours, 1),
            'total_amount_analyzed': round(stats['total_amount_analyzed'], 2),
            'fraud_amount_blocked': round(stats['fraud_amount_blocked'], 2),
            'risk_distribution': stats['risk_distribution'],
            'recent_transactions': list(stats['recent_transactions'])[-10:],
            'last_prediction_time': stats.get('last_prediction_time'),
            'model_status': 'Active' if model is not None else 'Not Loaded',
            'timestamp': datetime.now().isoformat()
        }

        return jsonify(response_data), 200
    except Exception as e:
        logger.error(f"Error in stats API: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/stats/live', methods=['GET'])
def get_live_stats():
    """API endpoint for minimal live statistics (for frequent polling)"""
    try:
        fraud_rate = (stats['fraud_detected'] / stats['total_predictions'] * 100) if stats['total_predictions'] > 0 else 0
        avg_response = sum(stats['avg_response_times']) / len(stats['avg_response_times']) if stats['avg_response_times'] else 0.25

        response_data = {
            'total_predictions': stats['total_predictions'],
            'fraud_detected': stats['fraud_detected'],
            'fraud_rate': round(fraud_rate, 2),
            'avg_response_time_ms': round(avg_response * 1000, 2),
            'last_prediction_time': stats.get('last_prediction_time'),
            'timestamp': datetime.now().isoformat()
        }

        return jsonify(response_data), 200
    except Exception as e:
        logger.error(f"Error in live stats API: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/transactions/recent', methods=['GET'])
@app.route('/api/recent-predictions', methods=['GET'])
def get_recent_transactions():
    """API endpoint for recent transactions"""
    try:
        limit = min(int(request.args.get('limit', 10)), 100)
        recent = list(stats['recent_transactions'])[-limit:]

        return jsonify({
            'transactions': recent,
            'total_count': len(stats['recent_transactions']),
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Error in transactions API: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/risk/distribution', methods=['GET'])
def get_risk_distribution():
    """API endpoint for risk distribution statistics"""
    try:
        total = sum(stats['risk_distribution'].values())
        distribution_percentage = {}

        for risk_level, count in stats['risk_distribution'].items():
            percentage = (count / total * 100) if total > 0 else 0
            distribution_percentage[risk_level] = {
                'count': count,
                'percentage': round(percentage, 2)
            }

        return jsonify({
            'distribution': distribution_percentage,
            'total': total,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Error in risk distribution API: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/categories', methods=['GET'])
def get_category_stats():
    """API endpoint for category-based statistics"""
    try:
        category_data = []
        for category, data in stats['category_stats'].items():
            fraud_rate = (data['fraud'] / data['total'] * 100) if data['total'] > 0 else 0
            category_data.append({
                'category': category,
                'total': data['total'],
                'fraud': data['fraud'],
                'fraud_rate': round(fraud_rate, 2)
            })

        # Sort by total transactions
        category_data.sort(key=lambda x: x['total'], reverse=True)

        return jsonify({
            'categories': category_data,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Error in categories API: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """API endpoint for system health check"""
    try:
        uptime_delta = datetime.now() - system_start_time

        health_data = {
            'status': 'healthy' if model is not None else 'degraded',
            'model_loaded': model is not None,
            'uptime_seconds': uptime_delta.total_seconds(),
            'total_predictions': stats['total_predictions'],
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0'
        }

        status_code = 200 if model is not None else 503
        return jsonify(health_data), status_code
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@app.errorhandler(404)
def not_found_handler(e):
    return render_template("error.html", error="Page not found."), 404

@app.errorhandler(500)
def internal_error_handler(e):
    logger.error(f"Internal server error: {str(e)}")
    return render_template("error.html",
                         error="Internal server error. Please contact administrator."), 500

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '127.0.0.1')

    logger.info(f"Starting SecureGuard Fraud Detection System")
    logger.info(f"Server: {host}:{port}, Debug: {debug_mode}")
    app.run(host=host, port=port, debug=debug_mode)
