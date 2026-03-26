@echo off
echo Creating virtual environment...
py -3.12 -m venv .venv

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Upgrading pip...
.venv\Scripts\python.exe -m pip install --upgrade pip

echo Installing dependencies from requirements.txt...
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

echo.
echo Starting sub-site servers...
for /D %%d in (Websites\*) do (
    if exist "%%d\backend\server.py" (
        echo   Starting %%~nxd ...
        start /B python "%%d\backend\server.py"
    )
)

echo Starting main server...
python backend\server.py
pause
