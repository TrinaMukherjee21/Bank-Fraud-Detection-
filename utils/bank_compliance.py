"""
Bank compliance and security utilities for fraud detection system.

This module provides:
- Data masking for sensitive information
- Compliance flag checking
- Enhanced audit logging utilities
"""

import re
from typing import Dict, Any, List
from flask import request
import hashlib


def mask_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mask sensitive customer and financial data for logging and display.

    Args:
        data: Dictionary containing potentially sensitive data

    Returns:
        Dictionary with sensitive fields masked
    """
    masked_data = data.copy()

    # Mask customer ID - show only last 4 digits
    if 'customer' in masked_data and masked_data['customer']:
        customer_str = str(masked_data['customer'])
        if len(customer_str) > 4:
            masked_data['customer'] = f"***{customer_str[-4:]}"
        else:
            masked_data['customer'] = "***" + customer_str

    # Mask amount - show range instead of exact amount for large transactions
    if 'amount' in masked_data and masked_data['amount']:
        amount = float(masked_data['amount'])
        if amount >= 10000:
            # For large amounts, show range only
            if amount < 50000:
                masked_data['amount_range'] = "$10K-$50K"
            elif amount < 100000:
                masked_data['amount_range'] = "$50K-$100K"
            else:
                masked_data['amount_range'] = "$100K+"
            # Keep exact amount but mark as sensitive
            masked_data['amount'] = f"[SENSITIVE: {amount:.2f}]"

    # Hash any PII fields if present
    pii_fields = ['email', 'phone', 'ssn', 'account_number']
    for field in pii_fields:
        if field in masked_data and masked_data[field]:
            # Create a consistent hash for the same value
            hash_value = hashlib.sha256(str(masked_data[field]).encode()).hexdigest()[:8]
            masked_data[field] = f"[HASH:{hash_value}]"

    return masked_data


def check_compliance_flags(transaction_data: Dict[str, Any]) -> List[str]:
    """
    Check transaction against regulatory compliance thresholds.

    Args:
        transaction_data: Transaction details including amount, customer info

    Returns:
        List of compliance flags that need attention
    """
    flags = []
    amount = float(transaction_data.get('amount', 0))

    # Currency Transaction Report (CTR) - $10,000 threshold
    if amount >= 10000:
        flags.append("CTR_REQUIRED")
        flags.append("HIGH_VALUE_TRANSACTION")

    # Suspicious Activity Report (SAR) consideration - $3,000 threshold
    if amount >= 3000:
        flags.append("SAR_REVIEW_REQUIRED")

    # Large cash transaction - $5,000 threshold
    if amount >= 5000:
        flags.append("LARGE_CASH_EQUIVALENT")

    # Very high risk threshold - $50,000
    if amount >= 50000:
        flags.append("EXECUTIVE_APPROVAL_REQUIRED")
        flags.append("ENHANCED_DUE_DILIGENCE")

    # Structuring detection - amounts just below reporting thresholds
    if 9000 <= amount < 10000:
        flags.append("POTENTIAL_STRUCTURING")

    # Round amount patterns (potential money laundering indicator)
    if amount % 1000 == 0 and amount >= 5000:
        flags.append("ROUND_AMOUNT_PATTERN")

    # Cross-border considerations (if international transaction)
    if transaction_data.get('international', False):
        if amount >= 3000:
            flags.append("INTERNATIONAL_WIRE_REVIEW")
        flags.append("AML_ENHANCED_SCREENING")

    return flags


def get_enhanced_audit_data(request_obj, session_data: Dict, transaction_data: Dict) -> Dict[str, Any]:
    """
    Collect comprehensive audit data for compliance logging.

    Args:
        request_obj: Flask request object
        session_data: Session information
        transaction_data: Transaction details

    Returns:
        Enhanced audit data dictionary
    """
    # Get client information
    client_ip = request_obj.environ.get('HTTP_X_FORWARDED_FOR',
                                       request_obj.environ.get('REMOTE_ADDR', 'unknown'))
    user_agent = request_obj.headers.get('User-Agent', 'unknown')

    # Create audit data
    audit_data = {
        # Request metadata
        'client_ip': client_ip,
        'user_agent': user_agent,
        'request_method': request_obj.method,
        'request_url': request_obj.url,
        'request_timestamp': transaction_data.get('timestamp'),

        # Session information
        'session_id': session_data.get('session_id', 'unknown'),
        'session_duration': session_data.get('duration', 'unknown'),

        # Transaction data (masked)
        'masked_transaction_data': mask_sensitive_data(transaction_data),

        # Compliance flags
        'compliance_flags': check_compliance_flags(transaction_data),

        # Risk assessment
        'risk_level': transaction_data.get('risk_level', 'unknown'),
        'fraud_probability': transaction_data.get('fraud_probability', 0),

        # Processing metadata
        'model_version': transaction_data.get('model_version', 'unknown'),
        'processing_time_ms': transaction_data.get('processing_time', 0) * 1000
    }

    return audit_data


def validate_transaction_limits(transaction_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate transaction against bank-specific limits and policies.

    Args:
        transaction_data: Transaction details

    Returns:
        Dictionary with validation results and any limit violations
    """
    violations = []
    warnings = []
    amount = float(transaction_data.get('amount', 0))

    # Daily transaction limits
    DAILY_LIMIT = 100000  # $100K daily limit
    if amount > DAILY_LIMIT:
        violations.append(f"Exceeds daily transaction limit: ${DAILY_LIMIT:,}")

    # Single transaction limits
    SINGLE_TRANSACTION_LIMIT = 250000  # $250K single transaction limit
    if amount > SINGLE_TRANSACTION_LIMIT:
        violations.append(f"Exceeds single transaction limit: ${SINGLE_TRANSACTION_LIMIT:,}")

    # Velocity checks (would need historical data in real implementation)
    # For now, just flag high-frequency patterns
    step = transaction_data.get('step', 0)
    if step > 700:  # Late in the day
        warnings.append("High-frequency transaction pattern detected")

    # Weekend/holiday checks (simplified)
    import datetime
    now = datetime.datetime.now()
    if now.weekday() >= 5:  # Saturday or Sunday
        warnings.append("Weekend transaction - enhanced monitoring")

    return {
        'is_valid': len(violations) == 0,
        'violations': violations,
        'warnings': warnings,
        'requires_approval': len(violations) > 0 or amount >= 50000
    }


def generate_compliance_report(transaction_data: Dict, prediction_result: Dict) -> Dict[str, Any]:
    """
    Generate a compliance-focused report for the transaction analysis.

    Args:
        transaction_data: Original transaction data
        prediction_result: ML model prediction results

    Returns:
        Compliance report dictionary
    """
    flags = check_compliance_flags(transaction_data)
    limits_check = validate_transaction_limits(transaction_data)

    report = {
        'transaction_id': prediction_result.get('session_id', 'unknown'),
        'timestamp': transaction_data.get('timestamp'),
        'compliance_status': 'COMPLIANT' if limits_check['is_valid'] else 'NON_COMPLIANT',
        'regulatory_flags': flags,
        'limit_violations': limits_check['violations'],
        'warnings': limits_check['warnings'],
        'requires_manual_review': (
            prediction_result.get('prediction') == 1 or  # Fraud detected
            len(flags) > 0 or  # Compliance flags present
            limits_check['requires_approval']  # Amount thresholds
        ),
        'risk_assessment': {
            'fraud_probability': prediction_result.get('fraud_probability', 0),
            'risk_level': prediction_result.get('risk_level', 'Unknown'),
            'confidence': prediction_result.get('confidence', 0)
        },
        'recommended_actions': _get_recommended_actions(flags, prediction_result, limits_check)
    }

    return report


def _get_recommended_actions(flags: List[str], prediction_result: Dict, limits_check: Dict) -> List[str]:
    """Generate recommended actions based on analysis results."""
    actions = []

    # Fraud-based actions
    if prediction_result.get('prediction') == 1:
        actions.append("🚨 BLOCK TRANSACTION - Fraud detected")
        actions.append("📞 Contact customer immediately for verification")

    # Compliance-based actions
    if "CTR_REQUIRED" in flags:
        actions.append("📋 File Currency Transaction Report (CTR)")

    if "SAR_REVIEW_REQUIRED" in flags:
        actions.append("🔍 Review for Suspicious Activity Report (SAR)")

    if "EXECUTIVE_APPROVAL_REQUIRED" in flags:
        actions.append("👔 Escalate to executive approval")

    if "ENHANCED_DUE_DILIGENCE" in flags:
        actions.append("🔎 Conduct enhanced due diligence")

    # Limit violation actions
    if limits_check['violations']:
        actions.append("⚠️ Manual approval required - Limit exceeded")

    if not actions:
        actions.append("✅ No immediate action required - Monitor transaction")

    return actions