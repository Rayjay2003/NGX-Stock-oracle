@echo off
cd /d "C:\Users\PC\Desktop\test"
call "%USERPROFILE%\Desktop\clean-venv\Scripts\activate"
cd keeper
python ngx_oracle_keeper.py
pause