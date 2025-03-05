import os
import subprocess
import sys
import time
import threading

def run_fastapi():
    subprocess.run([sys.executable, "-m", "uvicorn", "backend.fastapi_app:app", "--reload", "--port", "8000"])

def run_streamlit():
    # Give the backend a moment to start
    time.sleep(2)
    subprocess.run([sys.executable, "-m", "streamlit", "run", "frontend/app.py"])

if __name__ == "__main__":
    print("Dil Öğrenme Uygulaması başlatılıyor...")
    
    # Start FastAPI backend
    fastapi_thread = threading.Thread(target=run_fastapi)
    fastapi_thread.daemon = True
    fastapi_thread.start()
    
    print("Backend başlatıldı: http://localhost:8000")
    
    # Start Streamlit frontend
    print("Frontend başlatılıyor...")
    run_streamlit() 