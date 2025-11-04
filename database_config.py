"""
Database configuration and connection management for bank-scale fraud detection system.

This module provides database connectivity, connection pooling, and configuration
for production-ready transaction processing and fraud detection logging.
"""

import os
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
import mysql.connector
from mysql.connector import pooling
import sqlite3
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Database configuration manager"""
    
    def __init__(self):
        self.db_type = os.environ.get('DB_TYPE', 'sqlite')  # sqlite, mysql, postgresql
        self.host = os.environ.get('DB_HOST', 'localhost')
        self.port = int(os.environ.get('DB_PORT', '3306'))
        self.database = os.environ.get('DB_NAME', 'fraud_detection')
        self.username = os.environ.get('DB_USER', 'root')
        self.password = os.environ.get('DB_PASSWORD', '')
        self.pool_name = 'fraud_detection_pool'
        self.pool_size = int(os.environ.get('DB_POOL_SIZE', '20'))
        self.max_overflow = int(os.environ.get('DB_MAX_OVERFLOW', '30'))
        
        # SQLite file for development/testing
        self.sqlite_file = os.environ.get('DB_SQLITE_FILE', 'fraud_detection.db')

class DatabaseManager:
    """Database connection and operations manager"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connection_pool = None
        self._initialize_connection_pool()
        self._create_tables()
    
    def _initialize_connection_pool(self):
        """Initialize database connection pool"""
        try:
            if self.config.db_type == 'mysql':
                pool_config = {
                    'pool_name': self.config.pool_name,
                    'pool_size': self.config.pool_size,
                    'pool_reset_session': True,
                    'host': self.config.host,
                    'port': self.config.port,
                    'database': self.config.database,
                    'user': self.config.username,
                    'password': self.config.password,
                    'charset': 'utf8mb4',
                    'autocommit': True,
                    'time_zone': '+00:00'
                }
                self.connection_pool = pooling.MySQLConnectionPool(**pool_config)
                logger.info(f"MySQL connection pool initialized: {self.config.pool_size} connections")
                
            elif self.config.db_type == 'sqlite':
                # SQLite doesn't use connection pooling in the same way
                logger.info(f"SQLite database configured: {self.config.sqlite_file}")
                
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {str(e)}")
            raise

    @contextmanager
    def get_connection(self):
        """Get database connection from pool"""
        connection = None
        try:
            if self.config.db_type == 'mysql':
                connection = self.connection_pool.get_connection()
            elif self.config.db_type == 'sqlite':
                connection = sqlite3.connect(self.config.sqlite_file, timeout=30.0)
                connection.row_factory = sqlite3.Row  # Enable column access by name
                
            yield connection
            
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"Database connection error: {str(e)}")
            raise
        finally:
            if connection:
                connection.close()

    def _create_tables(self):
        """Create database tables if they don't exist"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.config.db_type == 'mysql':
                    self._create_mysql_tables(cursor)
                elif self.config.db_type == 'sqlite':
                    self._create_sqlite_tables(cursor)
                    
                conn.commit()
                logger.info("Database tables created/verified successfully")
                
        except Exception as e:
            logger.error(f"Failed to create database tables: {str(e)}")
            raise

    def _create_mysql_tables(self, cursor):
        """Create MySQL tables"""
        tables = {
            'transactions': """
                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id BIGINT PRIMARY KEY,
                    customer_id VARCHAR(50) NOT NULL,
                    amount DECIMAL(15,2) NOT NULL,
                    category_id INT NOT NULL,
                    merchant_id VARCHAR(50),
                    timestamp TIMESTAMP NOT NULL,
                    step_sequence INT,
                    age_group VARCHAR(20),
                    gender CHAR(1),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_customer_timestamp (customer_id, timestamp),
                    INDEX idx_amount (amount),
                    INDEX idx_timestamp (timestamp)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            
            'fraud_predictions': """
                CREATE TABLE IF NOT EXISTS fraud_predictions (
                    prediction_id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    transaction_id BIGINT NOT NULL,
                    session_id VARCHAR(50),
                    fraud_probability DECIMAL(5,4) NOT NULL,
                    prediction TINYINT(1) NOT NULL,
                    confidence_score DECIMAL(5,2) NOT NULL,
                    risk_level ENUM('Very Low', 'Low', 'Medium', 'High', 'Very High'),
                    model_version VARCHAR(20) NOT NULL,
                    processing_time_ms INT,
                    input_data JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_fraud_prediction (prediction),
                    INDEX idx_timestamp (created_at),
                    INDEX idx_risk_level (risk_level),
                    INDEX idx_session (session_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            
            'risk_factors': """
                CREATE TABLE IF NOT EXISTS risk_factors (
                    factor_id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    prediction_id BIGINT NOT NULL,
                    factor_type VARCHAR(100) NOT NULL,
                    factor_description TEXT,
                    severity_level ENUM('Low', 'Medium', 'High', 'Critical'),
                    FOREIGN KEY (prediction_id) REFERENCES fraud_predictions(prediction_id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            
            'system_metrics': """
                CREATE TABLE IF NOT EXISTS system_metrics (
                    metric_id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    metric_date DATE NOT NULL,
                    total_predictions INT DEFAULT 0,
                    fraud_detected INT DEFAULT 0,
                    avg_processing_time DECIMAL(8,4),
                    model_accuracy DECIMAL(5,4),
                    uptime_hours INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_metric_date (metric_date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            
            'audit_logs': """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    log_id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    session_id VARCHAR(50),
                    user_id VARCHAR(50),
                    action_type VARCHAR(50) NOT NULL,
                    entity_type VARCHAR(50),
                    entity_id BIGINT,
                    details JSON,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_session (session_id),
                    INDEX idx_timestamp (created_at),
                    INDEX idx_action_type (action_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        }
        
        for table_name, create_sql in tables.items():
            cursor.execute(create_sql)
            logger.debug(f"MySQL table '{table_name}' created/verified")

    def _create_sqlite_tables(self, cursor):
        """Create SQLite tables"""
        tables = {
            'transactions': """
                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id INTEGER PRIMARY KEY,
                    customer_id TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category_id INTEGER NOT NULL,
                    merchant_id TEXT,
                    timestamp TEXT NOT NULL,
                    step_sequence INTEGER,
                    age_group TEXT,
                    gender TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """,
            
            'fraud_predictions': """
                CREATE TABLE IF NOT EXISTS fraud_predictions (
                    prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id INTEGER NOT NULL,
                    session_id TEXT,
                    fraud_probability REAL NOT NULL,
                    prediction INTEGER NOT NULL,
                    confidence_score REAL NOT NULL,
                    risk_level TEXT,
                    model_version TEXT NOT NULL,
                    processing_time_ms INTEGER,
                    input_data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """,
            
            'risk_factors': """
                CREATE TABLE IF NOT EXISTS risk_factors (
                    factor_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_id INTEGER NOT NULL,
                    factor_type TEXT NOT NULL,
                    factor_description TEXT,
                    severity_level TEXT,
                    FOREIGN KEY (prediction_id) REFERENCES fraud_predictions(prediction_id)
                )
            """,
            
            'system_metrics': """
                CREATE TABLE IF NOT EXISTS system_metrics (
                    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_date TEXT NOT NULL,
                    total_predictions INTEGER DEFAULT 0,
                    fraud_detected INTEGER DEFAULT 0,
                    avg_processing_time REAL,
                    model_accuracy REAL,
                    uptime_hours INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(metric_date)
                )
            """,
            
            'audit_logs': """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    user_id TEXT,
                    action_type TEXT NOT NULL,
                    entity_type TEXT,
                    entity_id INTEGER,
                    details TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
        }
        
        for table_name, create_sql in tables.items():
            cursor.execute(create_sql)
            logger.debug(f"SQLite table '{table_name}' created/verified")

        # Create indexes for SQLite
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_transactions_customer_timestamp ON transactions(customer_id, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_amount ON transactions(amount)",
            "CREATE INDEX IF NOT EXISTS idx_predictions_fraud ON fraud_predictions(prediction)",
            "CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON fraud_predictions(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_predictions_session ON fraud_predictions(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_logs(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(created_at)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)

    def log_prediction(self, prediction_data: Dict[str, Any]) -> int:
        """Log fraud prediction to database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.config.db_type == 'mysql':
                    query = """
                        INSERT INTO fraud_predictions 
                        (transaction_id, session_id, fraud_probability, prediction, 
                         confidence_score, risk_level, model_version, processing_time_ms, input_data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    values = (
                        prediction_data.get('transaction_id', 0),
                        prediction_data.get('session_id'),
                        prediction_data['fraud_probability'],
                        prediction_data['prediction'],
                        prediction_data['confidence'],
                        prediction_data.get('risk_level'),
                        prediction_data.get('model_version', 'v1.0'),
                        int(prediction_data.get('processing_time', 0) * 1000),
                        str(prediction_data.get('input_data', {}))
                    )
                    
                elif self.config.db_type == 'sqlite':
                    query = """
                        INSERT INTO fraud_predictions 
                        (transaction_id, session_id, fraud_probability, prediction, 
                         confidence_score, risk_level, model_version, processing_time_ms, input_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    values = (
                        prediction_data.get('transaction_id', 0),
                        prediction_data.get('session_id'),
                        prediction_data['fraud_probability'],
                        prediction_data['prediction'],
                        prediction_data['confidence'],
                        prediction_data.get('risk_level'),
                        prediction_data.get('model_version', 'v1.0'),
                        int(prediction_data.get('processing_time', 0) * 1000),
                        str(prediction_data.get('input_data', {}))
                    )
                
                cursor.execute(query, values)
                
                if self.config.db_type == 'mysql':
                    prediction_id = cursor.lastrowid
                elif self.config.db_type == 'sqlite':
                    prediction_id = cursor.lastrowid
                    
                conn.commit()
                logger.debug(f"Prediction logged with ID: {prediction_id}")
                return prediction_id
                
        except Exception as e:
            logger.error(f"Failed to log prediction: {str(e)}")
            raise

    def get_recent_predictions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent fraud predictions"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.config.db_type == 'mysql':
                    query = """
                        SELECT prediction_id, session_id, fraud_probability, prediction,
                               confidence_score, risk_level, model_version, 
                               processing_time_ms, input_data, created_at
                        FROM fraud_predictions 
                        ORDER BY created_at DESC 
                        LIMIT %s
                    """
                    cursor.execute(query, (limit,))
                    
                elif self.config.db_type == 'sqlite':
                    query = """
                        SELECT prediction_id, session_id, fraud_probability, prediction,
                               confidence_score, risk_level, model_version, 
                               processing_time_ms, input_data, created_at
                        FROM fraud_predictions 
                        ORDER BY created_at DESC 
                        LIMIT ?
                    """
                    cursor.execute(query, (limit,))
                
                results = cursor.fetchall()
                
                predictions = []
                for row in results:
                    if self.config.db_type == 'mysql':
                        pred = {
                            'prediction_id': row[0],
                            'session_id': row[1],
                            'fraud_probability': float(row[2]),
                            'prediction': row[3],
                            'confidence': float(row[4]),
                            'risk_level': row[5],
                            'model_version': row[6],
                            'processing_time': row[7] / 1000.0 if row[7] else 0,
                            'input_data': eval(row[8]) if row[8] else {},
                            'timestamp': row[9].isoformat() if row[9] else None
                        }
                    elif self.config.db_type == 'sqlite':
                        pred = {
                            'prediction_id': row[0],
                            'session_id': row[1],
                            'fraud_probability': float(row[2]) if row[2] is not None else 0.0,
                            'prediction': int(row[3]) if row[3] is not None else 0,
                            'confidence': float(row[4]) if row[4] is not None else 0.0,
                            'risk_level': row[5],
                            'model_version': row[6],
                            'processing_time': float(row[7]) / 1000.0 if row[7] else 0.0,
                            'input_data': eval(row[8]) if row[8] else {},
                            'timestamp': row[9]
                        }
                    predictions.append(pred)
                
                return predictions
                
        except Exception as e:
            logger.error(f"Failed to get recent predictions: {str(e)}")
            return []

    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics from database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get total predictions
                cursor.execute("SELECT COUNT(*) FROM fraud_predictions")
                total_predictions = cursor.fetchone()[0]
                
                # Get fraud count
                cursor.execute("SELECT COUNT(*) FROM fraud_predictions WHERE prediction = 1")
                fraud_detected = cursor.fetchone()[0]
                
                # Get average confidence
                cursor.execute("SELECT AVG(confidence_score) FROM fraud_predictions")
                avg_confidence_result = cursor.fetchone()
                avg_confidence = float(avg_confidence_result[0]) if avg_confidence_result[0] else 0.0
                
                # Get average processing time
                cursor.execute("SELECT AVG(processing_time_ms) FROM fraud_predictions WHERE processing_time_ms > 0")
                avg_time_result = cursor.fetchone()
                avg_processing_time = float(avg_time_result[0]) / 1000.0 if avg_time_result[0] else 0.0
                
                return {
                    'total_predictions': total_predictions,
                    'fraud_detected': fraud_detected,
                    'legitimate_transactions': total_predictions - fraud_detected,
                    'fraud_rate': (fraud_detected / total_predictions * 100) if total_predictions > 0 else 0,
                    'avg_confidence': avg_confidence,
                    'avg_processing_time': avg_processing_time
                }
                
        except Exception as e:
            logger.error(f"Failed to get system stats: {str(e)}")
            return {
                'total_predictions': 0,
                'fraud_detected': 0,
                'legitimate_transactions': 0,
                'fraud_rate': 0,
                'avg_confidence': 0,
                'avg_processing_time': 0
            }

    def cleanup_old_data(self, days_to_keep: int = 90):
        """Clean up old data for compliance and performance"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.config.db_type == 'mysql':
                    cursor.execute(
                        "DELETE FROM fraud_predictions WHERE created_at < %s",
                        (cutoff_date,)
                    )
                    cursor.execute(
                        "DELETE FROM audit_logs WHERE created_at < %s",
                        (cutoff_date,)
                    )
                elif self.config.db_type == 'sqlite':
                    cursor.execute(
                        "DELETE FROM fraud_predictions WHERE created_at < ?",
                        (cutoff_date.isoformat(),)
                    )
                    cursor.execute(
                        "DELETE FROM audit_logs WHERE created_at < ?",
                        (cutoff_date.isoformat(),)
                    )
                
                conn.commit()
                logger.info(f"Cleaned up data older than {days_to_keep} days")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {str(e)}")

    def log_audit_entry(self, log_entry: Dict[str, Any]) -> int:
        """Log audit entry to database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.config.db_type == 'mysql':
                    query = """
                        INSERT INTO audit_logs 
                        (session_id, user_id, action_type, entity_type, entity_id, 
                         details, ip_address, user_agent, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    values = (
                        log_entry.get('session_id'),
                        log_entry.get('user_id'),
                        log_entry['action_type'],
                        log_entry.get('entity_type'),
                        log_entry.get('entity_id'),
                        log_entry.get('details'),
                        log_entry.get('ip_address'),
                        log_entry.get('user_agent'),
                        log_entry.get('timestamp')
                    )
                    
                elif self.config.db_type == 'sqlite':
                    query = """
                        INSERT INTO audit_logs 
                        (session_id, user_id, action_type, entity_type, entity_id, 
                         details, ip_address, user_agent, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    values = (
                        log_entry.get('session_id'),
                        log_entry.get('user_id'),
                        log_entry['action_type'],
                        log_entry.get('entity_type'),
                        log_entry.get('entity_id'),
                        log_entry.get('details'),
                        log_entry.get('ip_address'),
                        log_entry.get('user_agent'),
                        log_entry.get('timestamp')
                    )
                
                cursor.execute(query, values)
                
                if self.config.db_type == 'mysql':
                    log_id = cursor.lastrowid
                elif self.config.db_type == 'sqlite':
                    log_id = cursor.lastrowid
                    
                conn.commit()
                return log_id
                
        except Exception as e:
            logger.error(f"Failed to log audit entry: {str(e)}")
            return 0

# Global database manager instance
db_config = DatabaseConfig()
db_manager = DatabaseManager(db_config)