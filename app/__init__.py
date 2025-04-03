import os
from flask import Flask
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def create_app():
    app = Flask(__name__)

    # --- Core Configuration --- #
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'a_default_secret_key')

    # --- Brassica Configuration --- #
    app.config['BRASSICA_USERNAME'] = os.getenv('BRASSICA_USERNAME')
    app.config['BRASSICA_PASSWORD'] = os.getenv('BRASSICA_PASSWORD') # Assuming password is used for token
    # app.config['BRASSICA_API_KEY'] = os.getenv('BRASSICA_API_KEY') # Add if HMAC is needed
    app.config['BRASSICA_BASE_URL'] = os.getenv('BRASSICA_BASE_URL', 'https://bbussandbox.brassicagroup.com/BBusGateway')
    app.config['CALLBACK_URL'] = os.getenv('CALLBACK_URL') # URL for Brassica to send callbacks

    # --- Supabase Configuration --- #
    app.config['SUPABASE_URL'] = os.getenv('SUPABASE_URL')
    app.config['SUPABASE_SERVICE_KEY'] = os.getenv('SUPABASE_SERVICE_KEY')

    # --- Initialize Extensions & Context Processors (if any) --- #
    # Example: Initialize DB connection handling
    # from . import db
    # db.init_app(app) # If using the optional close_db function

    # --- Register Blueprints --- #
    from .api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    from .callbacks import bp as callbacks_bp
    app.register_blueprint(callbacks_bp, url_prefix='/callbacks')

    @app.route('/health')
    def health_check():
        # Optionally, add a check to ensure DB connection works
        # try:
        #     from .db import get_supabase_client
        #     client = get_supabase_client()
        #     # Perform a simple query, e.g., list tables or select 1
        #     # client.table('your_table_name').select('id', head=True).execute() # Example
        #     db_status = "OK"
        # except Exception as e:
        #     current_app.logger.error(f"Health check DB connection failed: {e}")
        #     db_status = "Error"
        # return jsonify({"status": "OK", "database": db_status}), 200
        return "OK", 200

    return app 