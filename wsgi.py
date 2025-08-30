"""
WSGI entry point for Super Simple Kiosk.

This module provides the WSGI application entry point for production deployment
using WSGI servers like Gunicorn or uWSGI.
"""

from super_simple_kiosk.app import create_app

# Create the Flask application instance for WSGI
app = create_app()

if __name__ == "__main__":
    app.run()
