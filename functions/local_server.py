#!/usr/bin/env python3
"""
Local development server for AlcoGuardian backend
Runs all endpoints without Google Cloud Functions framework
"""
import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS

# Set environment variables for local development
os.environ['GCP_PROJECT'] = 'alco-guardian-test-local'
os.environ['UPLOAD_BUCKET'] = 'test-bucket'
os.environ['STORAGE_BUCKET'] = 'test-bucket'
os.environ['GEMINI_LOCATION'] = 'us-central1'
os.environ['GEMINI_MODEL'] = 'gemini-2.0-flash-001'

# Mock Firebase admin initialization
import firebase_admin
from unittest.mock import MagicMock

# Check if Firebase is already initialized
if not firebase_admin._apps:
    # If not initialized, create a mock app
    firebase_admin._apps = {'[DEFAULT]': MagicMock()}
    
# Mock Firebase auth service
firebase_admin.auth = MagicMock()
firebase_admin.auth.verify_id_token = MagicMock(side_effect=Exception("Mock auth"))
firebase_admin.firestore = MagicMock()

# Mock Firestore client
mock_db = MagicMock()
firebase_admin.firestore.client = MagicMock(return_value=mock_db)

# Import main functions after mocking
from main import (
    get_drinks_master, chat, start_session, get_current_session,
    guardian_check, add_drink, drink, get_user_id
)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Helper to convert functions_framework handlers to Flask routes
def convert_handler(handler):
    def flask_handler():
        # Create a mock request object that matches functions_framework format
        class MockRequest:
            def __init__(self):
                self.method = request.method
                self.headers = request.headers
                self.files = request.files
                self.is_json = request.is_json
                
            def get_json(self):
                return request.get_json()
        
        mock_request = MockRequest()
        
        # Call the original handler
        response = handler(mock_request)
        
        # Handle different response formats
        if isinstance(response, tuple) and len(response) == 3:
            data, status, headers = response
            resp = app.response_class(
                response=data,
                status=status,
                headers=headers
            )
            return resp
        else:
            return response
    
    return flask_handler

# Register all endpoints
app.route('/get_drinks_master', methods=['GET', 'OPTIONS'])(convert_handler(get_drinks_master))
app.route('/chat', methods=['POST', 'OPTIONS'])(convert_handler(chat))
app.route('/start_session', methods=['POST', 'OPTIONS'])(convert_handler(start_session))
app.route('/get_current_session', methods=['GET', 'OPTIONS'])(convert_handler(get_current_session))
app.route('/guardian_check', methods=['GET', 'OPTIONS'])(convert_handler(guardian_check))
app.route('/add_drink', methods=['POST', 'OPTIONS'])(convert_handler(add_drink))
app.route('/drink', methods=['POST', 'OPTIONS'])(convert_handler(drink))

# Health check endpoint
@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "alco-guardian-backend"})

if __name__ == '__main__':
    print("🚀 Starting AlcoGuardian Local Development Server")
    print("📍 Server running on http://localhost:8080")
    print("\n📋 Available endpoints:")
    print("   GET  /health")
    print("   GET  /get_drinks_master")
    print("   POST /chat")
    print("   POST /start_session")
    print("   GET  /get_current_session")
    print("   GET  /guardian_check")
    print("   POST /add_drink")
    print("   POST /drink")
    print("\n⚠️  Note: Running with mocked Firebase services")
    print("Press Ctrl+C to stop the server\n")
    
    app.run(host='0.0.0.0', port=8080, debug=True)