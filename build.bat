@echo off
REM Step 1: Ensure Poetry is installed
where poetry >nul 2>&1
if errorlevel 1 (
    echo Poetry not found. Installing Poetry...
    pip install poetry
)

REM Step 2: Install dependencies in a virtual environment
poetry install >install_output.txt 2>&1
findstr /C:"pyproject.toml changed significantly since poetry.lock was last generated" install_output.txt >nul
if %ERRORLEVEL% EQU 0 (
    echo Detected outdated poetry.lock, running poetry lock...
    poetry lock
    echo Re-running poetry install...
    poetry install --no-root
) else (
    echo Poetry install completed without lock file errors.
)

del install_output.txt

@echo off
set TAG=%1

REM Inject the tag into the build (e.g. via environment variable or write it to a file)
echo %TAG% > version.txt

REM Replace version string in Python source (example below)
powershell -Command "(Get-Content config.py) -replace '__DEV__VERSION__', '%TAG%' | Set-Content config.py"

REM Step 3: Run PyInstaller using Poetry's environment
poetry run pyinstaller --clean --onefile --name "QualsSync_%TAG%" --add-data version.txt main.py

REM Step 4: Copy config.json.template to dist as config.json
copy /Y config.json.template dist\config.json

REM Step 5: Copy mappings.json to dist as default-mappings.json
copy /Y mappings.json dist\ default-mappings.json


echo Build complete. Executable is dist\QualsSync.exe
echo Remember to EDIT dist\config.json and enter the correct information (url, API key, ...)
pause
