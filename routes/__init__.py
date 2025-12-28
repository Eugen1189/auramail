"""
Routes package for AuraMail Flask application.
Contains all Flask Blueprints organized by functionality.
"""
from flask import Blueprint

# Import all blueprints
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.api import api_bp
from routes.export import export_bp
from routes.email import email_bp
from routes.monitoring import monitoring_bp


def register_blueprints(app):
    """
    Register all blueprints with the Flask application.
    
    Args:
        app: Flask application instance
    """
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(email_bp)
    app.register_blueprint(monitoring_bp)

