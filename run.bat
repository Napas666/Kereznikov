@echo off
cd /d "%~dp0"
pip install --no-index --find-links=wheels pymem customtkinter pywin32
python kereznikov.py
pause
