"""Setup script for AI Survey Generator."""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, cwd=None):
    """Run a command and return success status."""
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, check=True, 
                              capture_output=True, text=True)
        print(f"✅ {command}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {command}")
        print(f"Error: {e.stderr}")
        return False

def setup_backend():
    """Setup backend dependencies."""
    print("\n🔧 Setting up backend...")
    
    backend_dir = Path("backend")
    if not backend_dir.exists():
        print("❌ Backend directory not found")
        return False
    
    # Install Python dependencies
    if not run_command("pip install -r requirements.txt", cwd=backend_dir):
        return False
    
    # Download spaCy model
    if not run_command("python -m spacy download en_core_web_sm"):
        print("⚠️  spaCy model download failed, will use fallback parsing")
    
    return True

def setup_frontend():
    """Setup frontend dependencies."""
    print("\n🔧 Setting up frontend...")
    
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("❌ Frontend directory not found")
        return False
    
    # Install Node.js dependencies
    if not run_command("npm install", cwd=frontend_dir):
        return False
    
    return True

def create_directories():
    """Create necessary directories."""
    print("\n📁 Creating directories...")
    
    directories = [
        "knowledge_base/embeddings",
        "backend/logs",
        "frontend/build"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created {directory}")
    
    return True

def check_requirements():
    """Check system requirements."""
    print("🔍 Checking system requirements...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    print(f"✅ Python {sys.version}")
    
    # Check Node.js
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Node.js {result.stdout.strip()}")
        else:
            print("❌ Node.js not found")
            return False
    except FileNotFoundError:
        print("❌ Node.js not found")
        return False
    
    # Check npm
    try:
        result = subprocess.run(["npm", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ npm {result.stdout.strip()}")
        else:
            print("❌ npm not found")
            return False
    except FileNotFoundError:
        print("❌ npm not found")
        return False
    
    return True

def main():
    """Main setup function."""
    print("🚀 AI Survey Generator Setup")
    print("=" * 40)
    
    if not check_requirements():
        print("\n❌ System requirements not met")
        return False
    
    if not create_directories():
        print("\n❌ Failed to create directories")
        return False
    
    if not setup_backend():
        print("\n❌ Backend setup failed")
        return False
    
    if not setup_frontend():
        print("\n❌ Frontend setup failed")
        return False
    
    print("\n" + "=" * 40)
    print("✅ Setup completed successfully!")
    print("\n🚀 To start the application:")
    print("1. Backend: cd backend && python -m app.main")
    print("2. Frontend: cd frontend && npm start")
    print("\n📖 Visit http://localhost:3000 to use the application")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)