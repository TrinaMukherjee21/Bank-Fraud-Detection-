"""
Compliance and Data Retention Manager for Bank Fraud Detection System

This module handles data retention policies, audit logging, compliance reporting,
and automated cleanup procedures required for banking regulations.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from database_config import db_manager
import threading
import schedule
import time

logger = logging.getLogger(__name__)

class ComplianceManager:
    """Manages compliance, data retention, and audit logging"""
    
    def __init__(self):
        self.data_retention_days = int(os.environ.get('DATA_RETENTION_DAYS', '90'))
        self.audit_enabled = os.environ.get('AUDIT_ENABLED', 'true').lower() == 'true'
        self.compliance_report_frequency = os.environ.get('COMPLIANCE_REPORT_FREQUENCY', 'daily')
        self.backup_enabled = os.environ.get('BACKUP_ENABLED', 'true').lower() == 'true'
        
        # Start background compliance tasks
        self._start_compliance_scheduler()
    
    def log_audit_event(self, event_data: Dict[str, Any]) -> bool:
        """Log audit event for compliance tracking"""
        if not self.audit_enabled:
            return True
            
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                audit_entry = {
                    'session_id': event_data.get('session_id'),
                    'user_id': event_data.get('user_id', 'system'),
                    'action_type': event_data.get('action_type'),
                    'entity_type': event_data.get('entity_type'),
                    'entity_id': event_data.get('entity_id'),
                    'details': json.dumps(event_data.get('details', {})),
                    'ip_address': event_data.get('ip_address'),
                    'user_agent': event_data.get('user_agent'),
                    'created_at': datetime.now().isoformat()
                }
                
                if db_manager.config.db_type == 'mysql':
                    query = """
                        INSERT INTO audit_logs 
                        (session_id, user_id, action_type, entity_type, entity_id, 
                         details, ip_address, user_agent, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    values = (
                        audit_entry['session_id'], audit_entry['user_id'],
                        audit_entry['action_type'], audit_entry['entity_type'],
                        audit_entry['entity_id'], audit_entry['details'],
                        audit_entry['ip_address'], audit_entry['user_agent'],
                        audit_entry['created_at']
                    )
                elif db_manager.config.db_type == 'sqlite':
                    query = """
                        INSERT INTO audit_logs 
                        (session_id, user_id, action_type, entity_type, entity_id, 
                         details, ip_address, user_agent, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    values = (
                        audit_entry['session_id'], audit_entry['user_id'],
                        audit_entry['action_type'], audit_entry['entity_type'],
                        audit_entry['entity_id'], audit_entry['details'],
                        audit_entry['ip_address'], audit_entry['user_agent'],
                        audit_entry['created_at']
                    )
                
                cursor.execute(query, values)
                conn.commit()
                logger.debug(f"Audit event logged: {audit_entry['action_type']}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to log audit event: {str(e)}")
            return False
    
    def generate_compliance_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate compliance report for specified date range"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Fraud detection metrics
                if db_manager.config.db_type == 'mysql':
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as total_predictions,
                            SUM(CASE WHEN prediction = 1 THEN 1 ELSE 0 END) as fraud_detected,
                            AVG(confidence_score) as avg_confidence,
                            AVG(processing_time_ms) as avg_processing_time
                        FROM fraud_predictions 
                        WHERE created_at BETWEEN %s AND %s
                    """, (start_date.isoformat(), end_date.isoformat()))
                elif db_manager.config.db_type == 'sqlite':
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as total_predictions,
                            SUM(CASE WHEN prediction = 1 THEN 1 ELSE 0 END) as fraud_detected,
                            AVG(confidence_score) as avg_confidence,
                            AVG(processing_time_ms) as avg_processing_time
                        FROM fraud_predictions 
                        WHERE created_at BETWEEN ? AND ?
                    """, (start_date.isoformat(), end_date.isoformat()))
                
                fraud_metrics = cursor.fetchone()
                
                # Audit activity summary
                if db_manager.config.db_type == 'mysql':
                    cursor.execute("""
                        SELECT action_type, COUNT(*) as count
                        FROM audit_logs 
                        WHERE created_at BETWEEN %s AND %s
                        GROUP BY action_type
                    """, (start_date.isoformat(), end_date.isoformat()))
                elif db_manager.config.db_type == 'sqlite':
                    cursor.execute("""
                        SELECT action_type, COUNT(*) as count
                        FROM audit_logs 
                        WHERE created_at BETWEEN ? AND ?
                        GROUP BY action_type
                    """, (start_date.isoformat(), end_date.isoformat()))
                
                audit_summary = dict(cursor.fetchall())
                
                # Risk level distribution
                if db_manager.config.db_type == 'mysql':
                    cursor.execute("""
                        SELECT risk_level, COUNT(*) as count
                        FROM fraud_predictions 
                        WHERE created_at BETWEEN %s AND %s
                        GROUP BY risk_level
                    """, (start_date.isoformat(), end_date.isoformat()))
                elif db_manager.config.db_type == 'sqlite':
                    cursor.execute("""
                        SELECT risk_level, COUNT(*) as count
                        FROM fraud_predictions 
                        WHERE created_at BETWEEN ? AND ?
                        GROUP BY risk_level
                    """, (start_date.isoformat(), end_date.isoformat()))
                
                risk_distribution = dict(cursor.fetchall())
                
                report = {
                    'report_period': {
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat()
                    },
                    'fraud_detection_metrics': {
                        'total_predictions': fraud_metrics[0] if fraud_metrics else 0,
                        'fraud_detected': fraud_metrics[1] if fraud_metrics else 0,
                        'fraud_rate': (fraud_metrics[1] / fraud_metrics[0] * 100) if fraud_metrics and fraud_metrics[0] > 0 else 0,
                        'avg_confidence': float(fraud_metrics[2]) if fraud_metrics and fraud_metrics[2] else 0,
                        'avg_processing_time_ms': float(fraud_metrics[3]) if fraud_metrics and fraud_metrics[3] else 0
                    },
                    'audit_activity': audit_summary,
                    'risk_distribution': risk_distribution,
                    'compliance_status': {
                        'data_retention_policy': f"{self.data_retention_days} days",
                        'audit_logging': 'enabled' if self.audit_enabled else 'disabled',
                        'backup_policy': 'enabled' if self.backup_enabled else 'disabled'
                    },
                    'generated_at': datetime.now().isoformat(),
                    'generated_by': 'compliance_manager'
                }
                
                return report
                
        except Exception as e:
            logger.error(f"Failed to generate compliance report: {str(e)}")
            return {}
    
    def cleanup_old_data(self) -> Dict[str, int]:
        """Clean up old data according to retention policy"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.data_retention_days)
            cleanup_stats = {'predictions_deleted': 0, 'audit_logs_deleted': 0}
            
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Log cleanup action for audit
                self.log_audit_event({
                    'action_type': 'data_cleanup',
                    'entity_type': 'system',
                    'details': {
                        'cutoff_date': cutoff_date.isoformat(),
                        'retention_days': self.data_retention_days
                    }
                })
                
                # Delete old fraud predictions
                if db_manager.config.db_type == 'mysql':
                    cursor.execute(
                        "DELETE FROM fraud_predictions WHERE created_at < %s",
                        (cutoff_date,)
                    )
                    cleanup_stats['predictions_deleted'] = cursor.rowcount
                    
                    # Delete old audit logs (keep longer for compliance)
                    audit_cutoff = datetime.now() - timedelta(days=self.data_retention_days * 2)
                    cursor.execute(
                        "DELETE FROM audit_logs WHERE created_at < %s",
                        (audit_cutoff,)
                    )
                    cleanup_stats['audit_logs_deleted'] = cursor.rowcount
                    
                elif db_manager.config.db_type == 'sqlite':
                    cursor.execute(
                        "DELETE FROM fraud_predictions WHERE created_at < ?",
                        (cutoff_date.isoformat(),)
                    )
                    cleanup_stats['predictions_deleted'] = cursor.rowcount
                    
                    # Delete old audit logs (keep longer for compliance)
                    audit_cutoff = datetime.now() - timedelta(days=self.data_retention_days * 2)
                    cursor.execute(
                        "DELETE FROM audit_logs WHERE created_at < ?",
                        (audit_cutoff.isoformat(),)
                    )
                    cleanup_stats['audit_logs_deleted'] = cursor.rowcount
                
                conn.commit()
                
                logger.info(f"Data cleanup completed: {cleanup_stats}")
                return cleanup_stats
                
        except Exception as e:
            logger.error(f"Data cleanup failed: {str(e)}")
            return {'predictions_deleted': 0, 'audit_logs_deleted': 0}
    
    def export_audit_trail(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Export audit trail for compliance review"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                if db_manager.config.db_type == 'mysql':
                    cursor.execute("""
                        SELECT log_id, session_id, user_id, action_type, entity_type, 
                               entity_id, details, ip_address, user_agent, created_at
                        FROM audit_logs 
                        WHERE created_at BETWEEN %s AND %s
                        ORDER BY created_at DESC
                    """, (start_date.isoformat(), end_date.isoformat()))
                elif db_manager.config.db_type == 'sqlite':
                    cursor.execute("""
                        SELECT log_id, session_id, user_id, action_type, entity_type, 
                               entity_id, details, ip_address, user_agent, created_at
                        FROM audit_logs 
                        WHERE created_at BETWEEN ? AND ?
                        ORDER BY created_at DESC
                    """, (start_date.isoformat(), end_date.isoformat()))
                
                results = cursor.fetchall()
                
                audit_trail = []
                for row in results:
                    audit_entry = {
                        'log_id': row[0],
                        'session_id': row[1],
                        'user_id': row[2],
                        'action_type': row[3],
                        'entity_type': row[4],
                        'entity_id': row[5],
                        'details': json.loads(row[6]) if row[6] else {},
                        'ip_address': row[7],
                        'user_agent': row[8],
                        'created_at': row[9]
                    }
                    audit_trail.append(audit_entry)
                
                return audit_trail
                
        except Exception as e:
            logger.error(f"Failed to export audit trail: {str(e)}")
            return []
    
    def validate_data_integrity(self) -> Dict[str, Any]:
        """Validate data integrity for compliance"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                validation_results = {
                    'timestamp': datetime.now().isoformat(),
                    'checks_performed': [],
                    'issues_found': [],
                    'status': 'pass'
                }
                
                # Check for orphaned records
                if db_manager.config.db_type == 'mysql':
                    cursor.execute("""
                        SELECT COUNT(*) FROM risk_factors rf
                        LEFT JOIN fraud_predictions fp ON rf.prediction_id = fp.prediction_id
                        WHERE fp.prediction_id IS NULL
                    """)
                elif db_manager.config.db_type == 'sqlite':
                    cursor.execute("""
                        SELECT COUNT(*) FROM risk_factors rf
                        LEFT JOIN fraud_predictions fp ON rf.prediction_id = fp.prediction_id
                        WHERE fp.prediction_id IS NULL
                    """)
                
                orphaned_factors = cursor.fetchone()[0]
                validation_results['checks_performed'].append('orphaned_risk_factors')
                
                if orphaned_factors > 0:
                    validation_results['issues_found'].append({
                        'type': 'orphaned_records',
                        'description': f'Found {orphaned_factors} orphaned risk factors',
                        'severity': 'medium'
                    })
                    validation_results['status'] = 'warning'
                
                # Check for future timestamps (data integrity issue)
                future_date = datetime.now() + timedelta(hours=1)
                cursor.execute(
                    "SELECT COUNT(*) FROM fraud_predictions WHERE created_at > ?",
                    (future_date.isoformat(),)
                )
                
                future_records = cursor.fetchone()[0]
                validation_results['checks_performed'].append('future_timestamps')
                
                if future_records > 0:
                    validation_results['issues_found'].append({
                        'type': 'future_timestamps',
                        'description': f'Found {future_records} records with future timestamps',
                        'severity': 'high'
                    })
                    validation_results['status'] = 'fail'
                
                # Check for missing required fields
                cursor.execute("""
                    SELECT COUNT(*) FROM fraud_predictions 
                    WHERE session_id IS NULL OR prediction IS NULL OR confidence_score IS NULL
                """)
                
                missing_fields = cursor.fetchone()[0]
                validation_results['checks_performed'].append('missing_required_fields')
                
                if missing_fields > 0:
                    validation_results['issues_found'].append({
                        'type': 'missing_fields',
                        'description': f'Found {missing_fields} records with missing required fields',
                        'severity': 'high'
                    })
                    validation_results['status'] = 'fail'
                
                return validation_results
                
        except Exception as e:
            logger.error(f"Data integrity validation failed: {str(e)}")
            return {
                'timestamp': datetime.now().isoformat(),
                'status': 'error',
                'error': str(e)
            }
    
    def _start_compliance_scheduler(self):
        """Start background scheduler for compliance tasks"""
        def run_scheduler():
            # Schedule daily cleanup
            schedule.every().day.at("02:00").do(self.cleanup_old_data)
            
            # Schedule daily compliance report
            schedule.every().day.at("06:00").do(self._generate_daily_report)
            
            # Schedule weekly data integrity check
            schedule.every().sunday.at("03:00").do(self.validate_data_integrity)
            
            while True:
                schedule.run_pending()
                time.sleep(3600)  # Check every hour
        
        if os.environ.get('ENABLE_COMPLIANCE_SCHEDULER', 'true').lower() == 'true':
            scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
            scheduler_thread.start()
            logger.info("Compliance scheduler started")
    
    def _generate_daily_report(self):
        """Generate daily compliance report"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)
            
            report = self.generate_compliance_report(start_date, end_date)
            
            # Save report to file
            report_filename = f"compliance_report_{end_date.strftime('%Y%m%d')}.json"
            report_path = os.path.join('compliance_reports', report_filename)
            
            os.makedirs('compliance_reports', exist_ok=True)
            
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Daily compliance report generated: {report_path}")
            
            # Log audit event
            self.log_audit_event({
                'action_type': 'compliance_report_generated',
                'entity_type': 'report',
                'details': {
                    'report_file': report_filename,
                    'report_period': f"{start_date.date()} to {end_date.date()}"
                }
            })
            
        except Exception as e:
            logger.error(f"Failed to generate daily compliance report: {str(e)}")

# Global compliance manager instance
compliance_manager = ComplianceManager()