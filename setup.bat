@echo off
echo ========================================
echo   Face Recognition Attendance System
echo   Windows Environment Setup
echo ========================================
echo.

:: Check Python version
python --version 2>nul | findstr /r "3.1[01]" >nul
if errorlevel 1 (
    echo Checking Python...
    python --version
)

:: Remove old virtual environment if exists
if exist .venv (
    echo Removing existing virtual environment...
    rmdir /s /q .venv
    echo Done.
    echo.
)

:: Create virtual environment
echo Creating virtual environment...
python -m venv .venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment.
    pause
    exit /b 1
)
echo ✓ Virtual environment created.
echo.

:: Upgrade pip
echo Upgrading pip...
.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
echo.

:: Install dlib-bin first (prebuilt wheel, avoids CMake issues)
echo Installing dlib-bin (prebuilt wheel)...
.venv\Scripts\pip.exe install dlib-bin==20.0.0
if errorlevel 1 (
    echo ERROR: Failed to install dlib-bin.
    pause
    exit /b 1
)
echo ✓ dlib-bin installed.
echo.

:: Install face-recognition without pulling in regular dlib
echo Installing face-recognition...
.venv\Scripts\pip.exe install --no-deps face-recognition==1.3.0 face-recognition-models
if errorlevel 1 (
    echo ERROR: Failed to install face-recognition.
    pause
    exit /b 1
)
echo ✓ face-recognition installed.
echo.

:: Install remaining requirements
echo Installing remaining dependencies (this may take several minutes)...
.venv\Scripts\pip.exe install --no-cache-dir -r requirements.txt
echo.

:: Verify
echo Verifying installation...
.venv\Scripts\python.exe -c "import dlib; import face_recognition; import flask; print('All major packages imported successfully!')"
echo.

echo ========================================
echo   Setup complete!
echo ========================================
echo.
echo To activate the virtual environment, run:
echo   .venv\Scripts\activate
echo.
echo To start the application, run:
echo   python app.py
echo.
pause
