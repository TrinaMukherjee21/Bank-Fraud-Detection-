# Bank Fraud Detection System - Production Deployment Guide

This guide covers deploying the fraud detection system for bank-scale operations with proper database infrastructure, compliance features, and performance optimization.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │  Web Application │    │    Database     │
│   (nginx/ALB)   │───▶│   (Flask App)    │───▶│  (MySQL/PgSQL)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Compliance &    │
                       │ Audit Logging   │
                       └─────────────────┘
```

## Pre-Deployment Requirements

### System Requirements

**Production Server Specifications:**
- **CPU**: 8+ cores (Intel Xeon or AMD EPYC)
- **RAM**: 32GB+ (64GB recommended for high-volume processing)
- **Storage**: 500GB+ SSD (1TB+ for data retention)
- **Network**: Gigabit Ethernet, low latency connection
- **OS**: Ubuntu 20.04 LTS / CentOS 8 / RHEL 8

**Database Server Specifications:**
- **CPU**: 16+ cores for high-transaction volumes
- **RAM**: 64GB+ (128GB+ for large datasets)
- **Storage**: NVMe SSD with high IOPS (10,000+ IOPS recommended)
- **Network**: Dedicated network connection to application servers

### Security Requirements

- SSL/TLS certificates for HTTPS
- VPN or private network access
- Database encryption at rest
- Regular security updates
- Firewall configuration
- Intrusion detection system

## Database Setup

### 1. MySQL Production Setup

#### Installation
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install mysql-server-8.0

# CentOS/RHEL
sudo yum install mysql-server
sudo systemctl start mysqld
sudo systemctl enable mysqld
```

#### Configuration
```sql
-- Create database and user
CREATE DATABASE fraud_detection CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'fraud_user'@'%' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON fraud_detection.* TO 'fraud_user'@'%';
FLUSH PRIVILEGES;

-- Performance optimization
SET GLOBAL innodb_buffer_pool_size = 8G;  -- Adjust based on RAM
SET GLOBAL max_connections = 500;
SET GLOBAL query_cache_size = 256M;
```

#### MySQL Configuration File (`/etc/mysql/mysql.conf.d/mysqld.cnf`)
```ini
[mysqld]
# Performance settings
innodb_buffer_pool_size = 8G
innodb_log_file_size = 1G
innodb_flush_log_at_trx_commit = 2
max_connections = 500
table_open_cache = 4000
tmp_table_size = 256M
max_heap_table_size = 256M

# Security settings
bind-address = 10.0.0.0/8  # Adjust to your network
ssl-ca = /etc/mysql/ssl/ca.pem
ssl-cert = /etc/mysql/ssl/server-cert.pem
ssl-key = /etc/mysql/ssl/server-key.pem

# Logging
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 1
```

### 2. PostgreSQL Production Setup

#### Installation
```bash
# Ubuntu/Debian
sudo apt install postgresql-14 postgresql-contrib

# CentOS/RHEL
sudo yum install postgresql-server postgresql-contrib
sudo postgresql-setup initdb
```

#### Configuration
```sql
-- Create database and user
CREATE DATABASE fraud_detection;
CREATE USER fraud_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE fraud_detection TO fraud_user;
```

## Application Deployment

### 1. Environment Setup

Create production environment file:
```bash
cp .env.example .env
```

Edit `.env` for production:
```env
# Production Database Configuration
DB_TYPE=mysql
DB_HOST=your-database-server.com
DB_PORT=3306
DB_NAME=fraud_detection
DB_USER=fraud_user
DB_PASSWORD=your_secure_password
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=100

# Production Flask Configuration
SECRET_KEY=your-very-secure-secret-key-generate-new-one
FLASK_DEBUG=False
HOST=0.0.0.0
PORT=5000

# Security and Performance
RATELIMIT_STORAGE_URL=redis://localhost:6379/0
DATA_RETENTION_DAYS=90

# Compliance and Monitoring
ENABLE_COMPLIANCE_SCHEDULER=true
AUDIT_ENABLED=true
BACKUP_ENABLED=true

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
```

### 2. Application Installation

```bash
# Create application user
sudo useradd -m -s /bin/bash fraudapp
sudo su - fraudapp

# Clone and setup application
git clone <your-repo> fraud-detection
cd fraud-detection

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from database_config import db_manager; print('Database initialized successfully')"
```

### 3. Systemd Service Setup

Create `/etc/systemd/system/fraud-detection.service`:
```ini
[Unit]
Description=Bank Fraud Detection System
After=network.target mysql.service

[Service]
Type=simple
User=fraudapp
Group=fraudapp
WorkingDirectory=/home/fraudapp/fraud-detection
Environment=PATH=/home/fraudapp/fraud-detection/venv/bin
ExecStart=/home/fraudapp/fraud-detection/venv/bin/python app.py
Restart=always
RestartSec=5

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/fraudapp/fraud-detection

[Install]
WantedBy=multi-user.target
```

Enable and start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable fraud-detection
sudo systemctl start fraud-detection
```

### 4. Nginx Reverse Proxy

Install and configure Nginx:
```bash
sudo apt install nginx
```

Create `/etc/nginx/sites-available/fraud-detection`:
```nginx
upstream fraud_app {
    server 127.0.0.1:5000;
    # Add more servers for load balancing
    # server 127.0.0.1:5001;
    # server 127.0.0.1:5002;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL Configuration
    ssl_certificate /etc/ssl/certs/your-domain.crt;
    ssl_certificate_key /etc/ssl/private/your-domain.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=predict:10m rate=5r/s;

    location / {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://fraud_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /predict {
        limit_req zone=predict burst=10 nodelay;
        proxy_pass http://fraud_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files (if any)
    location /static {
        alias /home/fraudapp/fraud-detection/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/fraud-detection /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Performance Optimization

### 1. Database Optimization

#### Indexing Strategy
```sql
-- Essential indexes for performance
CREATE INDEX idx_predictions_created_at ON fraud_predictions(created_at);
CREATE INDEX idx_predictions_session ON fraud_predictions(session_id);
CREATE INDEX idx_predictions_fraud ON fraud_predictions(prediction);
CREATE INDEX idx_audit_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_action ON audit_logs(action_type);

-- Composite indexes for common queries
CREATE INDEX idx_predictions_date_fraud ON fraud_predictions(created_at, prediction);
CREATE INDEX idx_audit_session_action ON audit_logs(session_id, action_type);
```

#### Database Monitoring
```sql
-- Monitor slow queries
SELECT * FROM information_schema.processlist WHERE time > 5;

-- Check index usage
SELECT * FROM sys.schema_unused_indexes;

-- Monitor table sizes
SELECT 
    table_name,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size (MB)'
FROM information_schema.tables 
WHERE table_schema = 'fraud_detection'
ORDER BY (data_length + index_length) DESC;
```

### 2. Application Performance

#### Redis Configuration for Caching
```bash
# Install Redis
sudo apt install redis-server

# Configure Redis in /etc/redis/redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

#### Connection Pooling Optimization
Update `database_config.py` for production:
```python
# Production settings
DB_POOL_SIZE = int(os.environ.get('DB_POOL_SIZE', '50'))
DB_MAX_OVERFLOW = int(os.environ.get('DB_MAX_OVERFLOW', '100'))
DB_POOL_TIMEOUT = int(os.environ.get('DB_POOL_TIMEOUT', '30'))
DB_POOL_RECYCLE = int(os.environ.get('DB_POOL_RECYCLE', '3600'))
```

## Monitoring and Alerting

### 1. Application Monitoring

Install Prometheus and Grafana:
```bash
# Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.40.0/prometheus-2.40.0.linux-amd64.tar.gz
tar xvf prometheus-2.40.0.linux-amd64.tar.gz
sudo mv prometheus-2.40.0.linux-amd64/prometheus /usr/local/bin/
sudo mv prometheus-2.40.0.linux-amd64/promtool /usr/local/bin/

# Grafana
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
sudo apt-get update
sudo apt-get install grafana
```

### 2. Key Metrics to Monitor

- **Application Metrics**:
  - Response time per endpoint
  - Fraud detection accuracy
  - Prediction throughput
  - Error rates
  - Memory and CPU usage

- **Database Metrics**:
  - Connection pool utilization
  - Query execution time
  - Disk I/O
  - Table sizes
  - Index efficiency

- **System Metrics**:
  - Server CPU, memory, disk usage
  - Network latency
  - SSL certificate expiration
  - Log file sizes

### 3. Alerting Rules

Create alerting rules for:
- High fraud detection rate (potential attack)
- System downtime
- Database connection issues
- Unusual prediction patterns
- Performance degradation
- Security events

## Backup and Disaster Recovery

### 1. Database Backup Strategy

#### Automated MySQL Backups
```bash
#!/bin/bash
# /home/fraudapp/scripts/backup_db.sh

BACKUP_DIR="/backup/fraud_detection"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="fraud_detection_$DATE.sql"

# Create backup directory
mkdir -p $BACKUP_DIR

# Create backup
mysqldump --single-transaction --routines --triggers \
    --host=localhost --user=backup_user --password=backup_password \
    fraud_detection > $BACKUP_DIR/$BACKUP_FILE

# Compress backup
gzip $BACKUP_DIR/$BACKUP_FILE

# Keep only last 30 days of backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

# Upload to cloud storage (optional)
aws s3 cp $BACKUP_DIR/$BACKUP_FILE.gz s3://your-backup-bucket/database/
```

#### Schedule Backups
```bash
# Add to crontab (crontab -e)
0 2 * * * /home/fraudapp/scripts/backup_db.sh
```

### 2. Application Backup

- Model files and configurations
- Application code and dependencies
- Environment configurations
- Compliance reports

## Security Hardening

### 1. Network Security

- Firewall configuration (UFW/iptables)
- VPN access for administrative tasks
- Database access restriction
- SSL/TLS encryption for all communications

### 2. Application Security

- Input validation and sanitization
- Rate limiting and DDoS protection
- Regular security updates
- Audit logging for all activities
- Secure session management

### 3. Compliance Features

The system includes built-in compliance features:

- **Audit Logging**: All user actions and system events
- **Data Retention**: Automated cleanup based on retention policies
- **Compliance Reports**: Automated daily/weekly reports
- **Data Integrity Checks**: Regular validation of data consistency

## Scaling Considerations

### Horizontal Scaling

1. **Load Balancing**: Multiple application instances behind load balancer
2. **Database Scaling**: Read replicas, sharding for high volume
3. **Caching Layer**: Redis cluster for session and prediction caching
4. **Microservices**: Split prediction engine from web interface

### Vertical Scaling

1. **Server Upgrades**: More CPU, RAM, faster storage
2. **Database Optimization**: Better hardware, SSD storage
3. **Network Improvements**: Higher bandwidth, lower latency

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   - Check connection pool settings
   - Verify database server status
   - Review network connectivity

2. **Performance Problems**
   - Monitor database query performance
   - Check system resource usage
   - Review application logs

3. **Model Loading Failures**
   - Verify model file permissions
   - Check model compatibility
   - Review training logs

### Log Analysis

Key log files to monitor:
- Application logs: `/var/log/fraud-detection/app.log`
- Database logs: `/var/log/mysql/error.log`
- Nginx logs: `/var/log/nginx/access.log`, `/var/log/nginx/error.log`
- System logs: `/var/log/syslog`

## Maintenance

### Regular Tasks

1. **Daily**: Monitor system health, review alerts
2. **Weekly**: Check compliance reports, review performance metrics
3. **Monthly**: Update dependencies, security patches
4. **Quarterly**: Model retraining, performance optimization review

### Update Procedures

1. Test updates in staging environment
2. Schedule maintenance windows
3. Backup before updates
4. Gradual rollout with monitoring
5. Rollback plan preparation

This deployment guide provides a comprehensive foundation for running the fraud detection system in a production banking environment with proper security, compliance, and performance considerations.