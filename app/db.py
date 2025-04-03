import os
from supabase import create_client, Client
from flask import current_app, g

def get_supabase_client():
    """Connects to Supabase and returns the client instance."""
    # Use Flask's application context (g) to store the client per request
    # to avoid reconnecting on every database operation within a single request.
    if 'supabase_client' not in g:
        supabase_url = current_app.config.get('SUPABASE_URL')
        supabase_key = current_app.config.get('SUPABASE_SERVICE_KEY')
        
        if not supabase_url or not supabase_key:
            current_app.logger.error("Supabase URL or Service Key is not configured.")
            raise ValueError("Supabase configuration missing in environment variables.")
            
        try:
            g.supabase_client: Client = create_client(supabase_url, supabase_key)
            current_app.logger.info("Supabase client initialized.")
        except Exception as e:
            current_app.logger.error(f"Failed to initialize Supabase client: {e}")
            raise
            
    return g.supabase_client

# Optional: Add a function to close the connection if needed, 
# though supabase-py typically manages connections automatically.
# def close_supabase_client(e=None):
#     client = g.pop('supabase_client', None)
#     if client is not None:
#         # Supabase-py doesn't have an explicit close method for the client itself
#         # Connections are usually handled by the underlying libraries (e.g., postgrest-py)
#         current_app.logger.info("Supabase client removed from context.")

# Optional: Register the close function with Flask's app context teardown
# def init_app(app):
#     app.teardown_appcontext(close_supabase_client) 