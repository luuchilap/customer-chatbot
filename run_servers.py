#!/usr/bin/env python3
"""
Server runner for MongoDB Product Chatbot
Runs the FastAPI web server
"""

import subprocess
import sys
import os
import signal

# Use the Python installation that has all packages
PYTHON_EXE = r"C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\python.exe"

def run_fastapi_server():
    """Run the FastAPI web server"""
    print("🚀 Starting FastAPI web server...")
    os.system(f'"{PYTHON_EXE}" app.py')

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    print("\n🛑 Shutting down server...")
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handling
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🌟 MongoDB Product Chatbot - Starting Service")
    print("=" * 50)
    
    try:
        run_fastapi_server()
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        print("✅ Server stopped")