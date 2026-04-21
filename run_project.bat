@echo off
:: הפעלת הבאקאנד
start cmd /k "venv\Scripts\activate && uvicorn main:app --reload --host 0.0.0.0"

:: הפעלת ngrok (השתמשנו ב-ngrok.exe במקום רק ngrok כדי להיות בטוחים)
timeout /t 3
start cmd /k "ngrok http --domain=aracely-renownless-arlette.ngrok-free.dev 8000"