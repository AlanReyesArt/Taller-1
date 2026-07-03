@echo off
echo ========================================
echo  Levantando MCP de Rubricas UPAO
echo  Puerto: 8001
echo ========================================
cd /d "%~dp0mcp-rubricas"
pip install fastapi uvicorn pydantic -q
echo.
echo MCP disponible en: http://localhost:8001
echo Health check:      http://localhost:8001/health
echo Catalogo:          http://localhost:8001/catalogo
echo.
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
