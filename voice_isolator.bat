@echo off
rem Drag and drop a video onto this file, or run: voice_isolator.bat "C:\path\to\video.mp4"
if "%~1"=="" (
    echo Drag and drop a video onto this .bat file.
    pause
    exit /b 1
)
uv run --python 3.12 --script "%~dp0voice_isolator.py" %*
pause
