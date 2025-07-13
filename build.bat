@echo off
rem Clean previous builds
rmdir /s /q build
rmdir /s /q dist
del main.spec

rem Build the executable
pyinstaller --onefile --windowed main.py

echo Build complete. Find your executable in the dist\ folder.
pause
