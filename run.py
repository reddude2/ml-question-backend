"""
Development Server Runner
"""
import uvicorn
import os
import sys

if __name__ == "__main__":
    # Fix Windows encoding
    if sys.platform == "win32":
        os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    # Run without reload to avoid multiprocessing issues
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # ← Disabled reload
        log_level="info"
    )