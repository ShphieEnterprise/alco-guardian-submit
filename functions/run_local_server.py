#!/usr/bin/env python3
"""
Local server runner for AlcoGuardian backend
"""
import os
import subprocess
import sys

# Set environment variables for local development
os.environ['GCP_PROJECT'] = 'alco-guardian-test-local'
os.environ['UPLOAD_BUCKET'] = 'test-bucket'
os.environ['STORAGE_BUCKET'] = 'test-bucket'
os.environ['GEMINI_LOCATION'] = 'us-central1'
os.environ['GEMINI_MODEL'] = 'gemini-2.0-flash-001'
os.environ['DISABLE_AUTH'] = 'true'  # Disable auth for local testing

print("🚀 Starting AlcoGuardian backend server locally...")
print("📍 Server will run on http://localhost:8080")
print("🔧 Environment:")
print(f"   - Project: {os.environ['GCP_PROJECT']}")
print(f"   - Auth: Disabled for local testing")
print("\nAvailable endpoints:")
print("   - GET  http://localhost:8080/get_drinks_master")
print("   - POST http://localhost:8080/chat")
print("   - POST http://localhost:8080/start_session")
print("   - POST http://localhost:8080/add_drink")
print("   - POST http://localhost:8080/drink")
print("   - GET  http://localhost:8080/guardian_check")
print("   - GET  http://localhost:8080/get_current_session")
print("\nPress Ctrl+C to stop the server\n")

# Run the functions-framework server
try:
    subprocess.run([
        sys.executable, "-m", "functions_framework",
        "--target=transcribe",
        "--port=8080",
        "--debug"
    ])
except KeyboardInterrupt:
    print("\n👋 Server stopped")