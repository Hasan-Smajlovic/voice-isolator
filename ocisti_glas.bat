@echo off
rem Prevuci video na ovaj fajl (drag and drop) ili: ocisti_glas.bat "C:\put\do\videa.mp4"
if "%~1"=="" (
    echo Prevuci video na ovaj .bat fajl.
    pause
    exit /b 1
)
uv run --python 3.12 --script "%~dp0ocisti_glas.py" %*
pause
