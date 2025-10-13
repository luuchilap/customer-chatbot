#!/usr/bin/env python3
"""
Unified server runner for MongoDB Product Chatbot
Runs both FastAPI web server and FastMCP server
"""

import subprocess
import sys
import os
import signal
import time
from multiprocessing import Process

# Use the Python installation that has all packages
PYTHON_EXE = r"C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\python.exe"

def run_fastapi_server():
    """Run the FastAPI web server"""
    print("🚀 Starting FastAPI web server...")
    os.system(f'"{PYTHON_EXE}" app.py')

def run_mcp_server():
    """Run the FastMCP server"""
    print("🔧 Starting FastMCP server...")
    os.system(f'"{PYTHON_EXE}" mcp_server.py')

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    print("\n🛑 Shutting down servers...")
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handling
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🌟 MongoDB Product Chatbot - Starting All Services")
    print("=" * 50)
    
    # Start both servers in separate processes
    fastapi_process = Process(target=run_fastapi_server)
    mcp_process = Process(target=run_mcp_server)
    
    try:
        fastapi_process.start()
        time.sleep(2)  # Give FastAPI time to start
        mcp_process.start()
        
        print("\n✅ Services started successfully!")
        print("📱 FastAPI web interface: http://localhost:8000")
        print("🔧 MCP server: Available for AI assistant connections")
        print("📚 API documentation: http://localhost:8000/docs")
        print("\nPress Ctrl+C to stop all servers")
        
        # Wait for processes
        fastapi_process.join()
        mcp_process.join()
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        fastapi_process.terminate()
        mcp_process.terminate()
        fastapi_process.join()
        mcp_process.join()
        print("✅ All servers stopped")