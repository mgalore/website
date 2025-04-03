from functools import wraps
from flask import request, jsonify, g, current_app

from .db import get_supabase_client

def require_api_key(f):
    """Decorator to protect routes with API key authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({"error": "Missing X-API-Key header"}), 401

        try:
            supabase = get_supabase_client()
            # IMPORTANT: In a real app, hash the stored API key and compare hashes.
            # For now, we do a direct lookup (less secure).
            response = supabase.table('api_users')\
                             .select('id, username, is_active')\
                             .eq('api_key', api_key)\
                             .eq('is_active', True)\
                             .limit(1)\
                             .execute()

            if response.data and len(response.data) == 1:
                g.api_user = response.data[0] # Store user info in request context
                current_app.logger.info(f"Authenticated API user: {g.api_user['username']} (ID: {g.api_user['id']})")
                return f(*args, **kwargs)
            else:
                current_app.logger.warning(f"Invalid or inactive API key received: {api_key[:5]}...")
                return jsonify({"error": "Invalid or inactive API key"}), 401

        except Exception as e:
            current_app.logger.error(f"Error during API key authentication: {e}")
            return jsonify({"error": "Authentication error"}), 500
            
    return decorated_function 