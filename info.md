Flask backend: http://localhost:5000
FastAPI backend: http://localhost:8000
Streamlit frontend: http://localhost:8501

{
    "email": "test2@example.com",
    "username": "testuser2",
    "password": "testpassword"
  }

  backend calistirma:  uvicorn backend.fastapi_app:app --reload --port 8000

  frontendt calistirma: streamlit run frontend/app.py
