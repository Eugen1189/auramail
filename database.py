"""
Database configuration and models for AuraMail.
Uses SQLAlchemy ORM with connection pooling.
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import JSON, Index
from sqlalchemy.dialects.postgresql import JSONB

# Initialize SQLAlchemy
db = SQLAlchemy()


class ActionLog(db.Model):
    """
    Stores email processing action logs.
    Replaces auramail_log.json file.
    """
    __tablename__ = 'action_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    msg_id = db.Column(db.String(255), nullable=False, unique=True, index=True)
    subject = db.Column(db.Text, nullable=False)
    ai_category = db.Column(db.String(50), nullable=False, index=True)
    action_taken = db.Column(db.String(50), nullable=False, index=True)
    # Follow-up monitor fields
    is_followup_pending = db.Column(db.Boolean, default=False, nullable=False, index=True)
    expected_reply_date = db.Column(db.Date, nullable=True, index=True)
    followup_sent = db.Column(db.Boolean, default=False, nullable=False, index=True)
    reason = db.Column(db.Text)
    details = db.Column(JSON)  # Stores full classification dict
    
    def to_dict(self):
        """Convert to dictionary for compatibility with old JSON format."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'msg_id': self.msg_id,
            'message_id': self.msg_id,  # alias
            'subject': self.subject,
            'original_subject': self.subject,  # alias
            'ai_category': self.ai_category,
            'action_taken': self.action_taken,
            'is_followup_pending': self.is_followup_pending,
            'expected_reply_date': self.expected_reply_date.isoformat() if self.expected_reply_date else None,
            'followup_sent': self.followup_sent,
            'reason': self.reason,
            'ai_description': self.reason,  # alias
            'details': self.details
        }
    
    def __repr__(self):
        return f'<ActionLog {self.msg_id[:20]}... {self.action_taken}>'


class Progress(db.Model):
    """
    Stores current processing progress.
    Replaces progress.json file.
    Only one record should exist at a time (latest progress).
    """
    __tablename__ = 'progress'
    
    id = db.Column(db.Integer, primary_key=True)
    total = db.Column(db.Integer, default=0, nullable=False)
    current = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(db.String(50), default='Idle', nullable=False)
    details = db.Column(db.Text, default='')
    stats = db.Column(JSON, default=dict)  # Statistics dictionary
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Convert to dictionary for API/frontend compatibility."""
        total = self.total or 0
        current = self.current or 0
        progress_percentage = int((current / total * 100)) if total > 0 else 0
        
        return {
            'total': total,
            'current': current,
            'current_message': current,  # For frontend compatibility
            'total_messages': total,  # For frontend compatibility
            'status': self.status,
            'details': self.details,
            'current_email_subject': self.details,  # For frontend compatibility
            'stats': self.stats or {},
            'statistics': self.stats or {},  # For frontend compatibility
            'progress_percentage': progress_percentage
        }
    
    def __repr__(self):
        return f'<Progress {self.current}/{self.total} {self.status}>'


class Report(db.Model):
    """
    Stores sorting job reports.
    Replaces last_report.json file.
    """
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    total_processed = db.Column(db.Integer, default=0, nullable=False)
    important = db.Column(db.Integer, default=0)
    action_required = db.Column(db.Integer, default=0)
    newsletter = db.Column(db.Integer, default=0)
    social = db.Column(db.Integer, default=0)
    review = db.Column(db.Integer, default=0)
    archived = db.Column(db.Integer, default=0)  # Changed from deleted - we preserve all emails
    errors = db.Column(db.Integer, default=0)
    
    # Store full statistics as JSON for flexibility
    stats = db.Column(JSON, default=dict)
    
    def to_dict(self):
        """Convert to dictionary for API compatibility."""
        return {
            'total_processed': self.total_processed,
            'important': self.important,
            'action_required': self.action_required,
            'newsletter': self.newsletter,
            'social': self.social,
            'review': self.review,
            'archived': self.archived,
            'errors': self.errors
        }
    
    def __repr__(self):
        return f'<Report {self.total_processed} processed at {self.created_at}>'


def init_db(app):
    """
    Initialize database connection with connection pooling.
    
    Args:
        app: Flask application instance
    """
    from config import DATABASE_URL, DB_POOL_SIZE, DB_MAX_OVERFLOW, DB_POOL_RECYCLE
    
    # Configure SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # SQLite doesn't support pool_size and max_overflow
    # Only set these for non-SQLite databases (PostgreSQL, MySQL, etc.)
    database_uri = app.config.get('SQLALCHEMY_DATABASE_URI', DATABASE_URL)
    is_sqlite = database_uri.startswith('sqlite://')
    
    if is_sqlite:
        # SQLite-specific configuration (no connection pooling)
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'echo': False  # Set to True for SQL query logging
        }
    else:
        # PostgreSQL/MySQL/etc. - use connection pooling
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_size': DB_POOL_SIZE,
            'max_overflow': DB_MAX_OVERFLOW,
            'pool_recycle': DB_POOL_RECYCLE,
            'pool_pre_ping': True,  # Verify connections before using
            'echo': False  # Set to True for SQL query logging
        }
    
    # Initialize db with app
    db.init_app(app)
    
    return db


