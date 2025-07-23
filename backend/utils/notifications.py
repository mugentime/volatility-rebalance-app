"""
Notification and alerting utilities
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
import os
from datetime import datetime

from backend.models.database import db, SystemAlert

logger = logging.getLogger(__name__)

def send_alert(title: str, message: str, user_id: Optional[int] = None, 
               severity: str = 'INFO', alert_type: str = 'SYSTEM'):
    """Send alert notification and store in database"""
    try:
        # Store in database
        alert = SystemAlert(
            user_id=user_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            created_at=datetime.utcnow()
        )
        db.session.add(alert)
        db.session.commit()

        # Send email if configured and severity is high
        if severity in ['ERROR', 'CRITICAL']:
            send_email_notification(title, message, user_id)

        logger.info(f"Alert sent: {title} - {severity}")

    except Exception as e:
        logger.error(f"Failed to send alert: {e}")

def send_email_notification(subject: str, body: str, user_id: Optional[int] = None):
    """Send email notification"""
    try:
        smtp_server = os.getenv('SMTP_SERVER')
        smtp_port = int(os.getenv('SMTP_PORT', 587))
        smtp_username = os.getenv('SMTP_USERNAME')
        smtp_password = os.getenv('SMTP_PASSWORD')
        from_email = os.getenv('FROM_EMAIL', smtp_username)

        if not all([smtp_server, smtp_username, smtp_password]):
            logger.warning("Email configuration incomplete, skipping email notification")
            return

        # Get recipient email
        if user_id:
            from backend.models.database import User
            user = User.query.get(user_id)
            to_email = user.email if user else None
        else:
            to_email = os.getenv('ADMIN_EMAIL')

        if not to_email:
            logger.warning("No recipient email found")
            return

        # Create message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = f"[Binance Strategy Alert] {subject}"

        msg.attach(MIMEText(body, 'plain'))

        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        server.quit()

        logger.info(f"Email notification sent to {to_email}")

    except Exception as e:
        logger.error(f"Failed to send email notification: {e}")

def send_ltv_warning(user_id: int, current_ltv: float, portfolio_value: float):
    """Send LTV warning alert"""
    title = f"LTV Warning: {current_ltv:.2%}"
    message = f"""
    Your portfolio LTV has reached {current_ltv:.2%}.

    Portfolio Value: ${portfolio_value:,.2f}
    Current LTV: {current_ltv:.2%}
    Warning Threshold: 65%
    Danger Threshold: 70%

    The system will automatically rebalance to maintain safe levels.

    Please monitor your positions closely.
    """

    send_alert(title, message, user_id, 'WARNING', 'LTV_WARNING')

def send_liquidation_alert(user_id: int, current_ltv: float):
    """Send emergency liquidation alert"""
    title = f"EMERGENCY LIQUIDATION - LTV: {current_ltv:.2%}"
    message = f"""
    EMERGENCY LIQUIDATION EXECUTED

    Your portfolio has been liquidated due to LTV exceeding safe limits.
    Current LTV: {current_ltv:.2%}
    Emergency Threshold: 75%

    All positions have been closed to prevent further losses.

    Please review your account immediately.
    """

    send_alert(title, message, user_id, 'CRITICAL', 'LIQUIDATION')

def send_system_error(error_message: str, user_id: Optional[int] = None):
    """Send system error notification"""
    title = "System Error"
    message = f"""
    A system error has occurred:

    Error: {error_message}
    Time: {datetime.utcnow().isoformat()}

    The development team has been notified.
    """

    send_alert(title, message, user_id, 'ERROR', 'SYSTEM_ERROR')
