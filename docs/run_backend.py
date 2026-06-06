"""Script to run the backend server."""

import sys
import os
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

if __name__ == "__main__":
    import uvicorn
    from app.main import app
    from config import API_HOST, API_PORT, DEBUG
    
    print("🚀 Starting AI Survey Generator Backend")
    print(f"📍 Server: http://{API_HOST}:{API_PORT}")
    print(f"📚 API Docs: http://{API_HOST}:{API_PORT}/docs")
    print("=" * 50)
    
    uvicorn.run(
        app,
        host=API_HOST,
        port=API_PORT,
        reload=DEBUG,
        log_level="info"
    )