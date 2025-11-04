# SecureGuard Fraud Detection - Installation & Setup Guide

## Quick Start (5 Minutes)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- Flask (web framework)
- Flask-Login (authentication)
- Flask-Bcrypt (password hashing)
- PyJWT (token management)
- Chart.js (via CDN - no installation needed)
- All ML dependencies (XGBoost, scikit-learn, etc.)

### Step 2: Run the Application

```bash
python app.py
```

You should see:
```
* Running on http://127.0.0.1:5000
* Model and encoders loaded successfully
```

### Step 3: Access the System

1. Open your browser
2. Navigate to: `http://localhost:5000`
3. You'll be redirected to the login page

### Step 4: Login with Demo Account

Use any of these accounts:

| Role | Username | Password |
|------|----------|----------|
| Admin | admin | admin123 |
| Analyst | analyst | analyst123 |
| Viewer | viewer | viewer123 |

---

## Detailed Setup

### System Requirements

- **Python**: 3.8 or higher
- **OS**: Windows, macOS, or Linux
- **RAM**: Minimum 2GB (4GB recommended)
- **Disk Space**: 500MB for dependencies
- **Browser**: Modern browser (Chrome, Firefox, Safari, Edge)

### Environment Variables (Optional)

Create a `.env` file in the project root:

```env
# Flask Configuration
SECRET_KEY=your-secret-key-here-change-in-production
FLASK_ENV=development

# JWT Configuration
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production

# Security
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
```

### Full Installation Steps

#### 1. Clone or Download Project

```bash
cd "Bank Fraud Detection"
```

#### 2. Create Virtual Environment (Recommended)

**Windows**:
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux**:
```bash
python3 -m venv venv
source venv/bin/activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Verify Model Files

Ensure these files exist in `model/` directory:
- `fraud_model.pkl` - Trained XGBoost model
- `label_encoders.pkl` - Feature encoders
- `threshold.pkl` - Optimal prediction threshold

If missing, run the training notebook first:
```bash
jupyter notebook train_model.ipynb
```

#### 5. Start the Server

```bash
python app.py
```

The server will start on: `http://127.0.0.1:5000`

---

## Testing the Installation

### 1. Test Login

1. Go to `http://localhost:5000`
2. Login as **admin** / **admin123**
3. You should see the dashboard

### 2. Test Quick Scan

1. Click **Quick Scan** in navigation
2. Fill in test data (see [QUICK_TEST_REFERENCE.txt](QUICK_TEST_REFERENCE.txt))
3. Click "Analyze Transaction"
4. Verify results page appears

### 3. Test Analytics Dashboard

1. Login as **analyst** or **admin**
2. Click **Analytics** in navigation
3. Verify all 6 charts load
4. Charts should display data

### 4. Test Role-Based Access

1. Logout (click 🚪 icon)
2. Login as **viewer** / **viewer123**
3. Try to access **Analytics**
4. Expected: "Access denied" message
5. Verify viewer can only access Dashboard and About

---

## Troubleshooting

### Issue: "Module not found" errors

**Solution**:
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### Issue: "Model file not found"

**Solution**:
```bash
# Check if model files exist
ls model/

# If missing, run training notebook
jupyter notebook train_model.ipynb
```

### Issue: Port 5000 already in use

**Solution 1** - Stop other process:
```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <process_id> /F

# macOS/Linux
lsof -ti:5000 | xargs kill -9
```

**Solution 2** - Use different port:
Edit `app.py`, change last line:
```python
app.run(debug=True, port=5001)  # Changed from 5000
```

### Issue: Charts not loading

**Possible causes**:
1. No internet connection (Chart.js loaded from CDN)
2. Browser blocking scripts
3. Ad blocker interfering

**Solution**:
- Check internet connection
- Disable ad blockers
- Check browser console (F12) for errors

### Issue: Login fails with correct credentials

**Solution**:
1. Check that you're using correct demo accounts
2. Verify `models/user.py` exists
3. Check server logs for errors
4. Restart the application

### Issue: "Access denied" for Analytics

**Expected behavior**:
- Only Admin and Analyst roles can access Analytics
- Viewer role cannot access Analytics

**Solution**:
- Login with admin or analyst account
- If logged in as viewer, this is expected behavior

---

## File Structure Overview

```
Bank Fraud Detection/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── train_model.ipynb              # Model training notebook
│
├── models/                        # User models
│   └── user.py                    # User, UserStore, ActivityLog
│
├── utils/                         # Utilities
│   ├── preprocess.py              # Data preprocessing
│   └── auth.py                    # Authentication utilities
│
├── templates/                     # HTML templates
│   ├── base.html                  # Base template with nav
│   ├── home.html                  # Dashboard
│   ├── login.html                 # Login page
│   ├── form_basic.html            # Quick scan
│   ├── form_advanced.html         # Deep analysis
│   ├── analytics.html             # Charts dashboard
│   ├── result.html                # Prediction results
│   ├── about.html                 # System information
│   └── error.html                 # Error page
│
├── static/                        # Static assets
│   └── css/
│       └── main.css               # Main stylesheet
│
├── model/                         # ML models
│   ├── fraud_model.pkl            # Trained model
│   ├── label_encoders.pkl         # Encoders
│   └── threshold.pkl              # Optimal threshold
│
└── Data/                          # Training datasets
    └── (your datasets here)
```

---

## Production Deployment

### For Production Environment:

#### 1. Use Production WSGI Server

**Install Gunicorn** (recommended):
```bash
pip install gunicorn
```

**Run with Gunicorn**:
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

#### 2. Set Up Database

Replace in-memory storage with PostgreSQL:

```bash
pip install psycopg2-binary flask-sqlalchemy
```

Update user storage to use SQLAlchemy.

#### 3. Enable HTTPS

Use nginx as reverse proxy with SSL:

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### 4. Set Environment Variables

```bash
export SECRET_KEY="production-secret-key-here"
export JWT_SECRET_KEY="production-jwt-key-here"
export FLASK_ENV="production"
```

#### 5. Change Default Passwords

**CRITICAL**: Change all demo account passwords immediately!

Edit `models/user.py`:
```python
admin.set_password('STRONG-PASSWORD-HERE')
analyst.set_password('STRONG-PASSWORD-HERE')
viewer.set_password('STRONG-PASSWORD-HERE')
```

---

## Docker Deployment (Optional)

### Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

### Build and Run

```bash
docker build -t secureguard-fraud-detection .
docker run -p 5000:5000 secureguard-fraud-detection
```

---

## Performance Optimization

### 1. Enable Caching

```python
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@app.route('/api/stats')
@cache.cached(timeout=10)
def get_stats():
    # ...
```

### 2. Use Redis for Sessions

```bash
pip install redis flask-session
```

```python
from flask_session import Session

app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.from_url('redis://localhost:6379')
Session(app)
```

### 3. Database Connection Pooling

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    'postgresql://user:pass@localhost/db',
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20
)
```

---

## Monitoring & Logging

### Enable Production Logging

```python
import logging
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler('app.log', maxBytes=10000000, backupCount=5)
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)
```

### Monitor with Prometheus (Optional)

```bash
pip install prometheus-flask-exporter
```

```python
from prometheus_flask_exporter import PrometheusMetrics

metrics = PrometheusMetrics(app)
```

---

## Support & Resources

### Documentation
- [NEW_FEATURES_SUMMARY.md](NEW_FEATURES_SUMMARY.md) - Complete feature documentation
- [TEST_DATA_GUIDE.md](TEST_DATA_GUIDE.md) - Test scenarios and data
- [QUICK_TEST_REFERENCE.txt](QUICK_TEST_REFERENCE.txt) - Quick test reference

### Demo Credentials
- **Admin**: admin / admin123
- **Analyst**: analyst / analyst123
- **Viewer**: viewer / viewer123

### URLs
- **Dashboard**: http://localhost:5000/
- **Login**: http://localhost:5000/login
- **Quick Scan**: http://localhost:5000/form_basic
- **Deep Analysis**: http://localhost:5000/form_advanced
- **Analytics**: http://localhost:5000/analytics
- **About**: http://localhost:5000/about
- **API Stats**: http://localhost:5000/api/stats

---

## Security Checklist for Production

- [ ] Change all default passwords
- [ ] Set strong SECRET_KEY and JWT_SECRET_KEY
- [ ] Enable HTTPS/SSL
- [ ] Implement database storage (not in-memory)
- [ ] Enable CSRF protection
- [ ] Set up firewall rules
- [ ] Implement IP whitelisting for admin
- [ ] Enable security headers (Flask-Talisman)
- [ ] Regular security audits
- [ ] Implement backup strategy
- [ ] Set up monitoring and alerting
- [ ] Configure rate limiting per route
- [ ] Implement 2FA for admin accounts
- [ ] Regular dependency updates

---

**Installation Complete!** 🎉

You're now ready to use the SecureGuard Fraud Detection System with all professional features including authentication, authorization, and advanced analytics.

For questions or issues, refer to the troubleshooting section above or check the log files.
