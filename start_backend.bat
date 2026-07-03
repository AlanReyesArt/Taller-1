@echo off
echo ========================================
echo  Levantando Backend FastAPI UPAO
echo  Puerto: 8000
echo ========================================
cd /d "%~dp0backend"
pip install -r requirements.txt -q
echo.
echo Backend disponible en: http://localhost:8000
echo API docs:              http://localhost:8000/docs
echo.
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
