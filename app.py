import os
from datetime import datetime
from flask import Flask, render_template
from config import Config
from extensions import db, login_manager, csrf

# Import models so SQLAlchemy discovers them
import models


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Register blueprints
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.exchanges import exchanges_bp
    from routes.messages import messages_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(exchanges_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(admin_bp)

    # Context processors for all templates
    @app.context_processor
    def inject_global_data():
        return {
            'now': datetime.utcnow(),
            'app_name': 'Smart Swap',
            'models': models,
            'Notification': models.Notification
        }

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    # Security Headers Hook (OWASP Recommended)
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        # Content Security Policy that allows Bootstrap CDN, Icons, local scripts, and Jitsi Meet iframe
        response.headers['Content-Security-Policy'] = (
            "default-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://meet.jit.si; "
            "frame-src 'self' https://meet.jit.si; "
            "font-src 'self' https://cdn.jsdelivr.net;"
        )
        return response

    # Ensure upload directories exist
    with app.app_context():
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['AVATAR_FOLDER'], exist_ok=True)
        try:
            db.create_all()
        except Exception as err:
            app.logger.warning(f"Could not initialize tables on start: {err}")

    return app


app = create_app()

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() in ('1', 'true', 'yes')
    app.run(debug=debug_mode, host='127.0.0.1', port=5000)
