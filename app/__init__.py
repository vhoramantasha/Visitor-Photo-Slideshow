import os
from flask import Flask, send_from_directory
from app.config import Config
from app.database import init_db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload and data directories exist
    config_class.ensure_directories()
    
    # Initialize SQLite database
    init_db(config_class.DATABASE_PATH)

    # Register Blueprints
    from app.routes.views import views_bp
    from app.routes.api import api_bp
    from app.routes.stream import stream_bp

    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(stream_bp, url_prefix="/api")

    # Static uploads handler with caching headers
    @app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # Health check endpoint
    @app.route('/health')
    def health():
        return {"status": "healthy", "app": "visitor-slideshow"}

    return app
