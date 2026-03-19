@echo off
REM ============================================================================
REM GHL Sales Assistant - Deployment Script (Windows)
REM Usage: deploy.bat [--build] [--restart] [--logs] [--stop]
REM
REM Flags:
REM   --build    Force rebuild Docker images
REM   --restart  Restart containers
REM   --logs     Follow container logs
REM   --stop     Stop all containers
REM   (no flag)  Build + start (default)
REM ============================================================================

setlocal enabledelayedexpansion

set PROJECT_NAME=GHL Sales Assistant
set COMPOSE_FILE=docker-compose.yml
set ENV_FILE=backend\.env
set ENV_EXAMPLE=backend\.env.example

echo.
echo ==========================================
echo   %PROJECT_NAME% — Deploy
echo ==========================================
echo.

REM ── Parse arguments ──────────────────────────────────────────────
if "%~1"=="--build"   goto action_build
if "%~1"=="--restart" goto action_restart
if "%~1"=="--logs"    goto action_logs
if "%~1"=="--stop"    goto action_stop
if "%~1"==""          goto action_default
goto usage

REM ── Preflight checks ─────────────────────────────────────────────
:preflight
echo [INFO]  Running preflight checks...

REM Check Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed. Please install Docker Desktop.
    exit /b 1
)
for /f "delims=" %%v in ('docker --version') do echo [OK]    Docker found: %%v

REM Check Docker Compose (v2 plugin)
docker compose version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Compose is not available. Please install Docker Desktop with Compose plugin.
    exit /b 1
)
for /f "delims=" %%v in ('docker compose version --short') do echo [OK]    Docker Compose found: %%v

REM Check .env file
if not exist "%ENV_FILE%" (
    echo [WARN]  .env file not found at %ENV_FILE%
    if exist "%ENV_EXAMPLE%" (
        copy "%ENV_EXAMPLE%" "%ENV_FILE%" >nul
        echo [WARN]  Copied %ENV_EXAMPLE% to %ENV_FILE%
        echo [WARN]  ^>^>^> EDIT %ENV_FILE% with your actual credentials before proceeding! ^<^<^<
        echo.
        pause
    ) else (
        echo [ERROR] No .env.example found either. Create %ENV_FILE% manually.
        exit /b 1
    )
) else (
    echo [OK]    .env file exists at %ENV_FILE%
)

echo [OK]    Preflight checks passed.
echo.
goto :eof

REM ── Actions ──────────────────────────────────────────────────────

:action_default
call :preflight
echo [INFO]  Building and starting %PROJECT_NAME%...
docker compose -f %COMPOSE_FILE% up -d --build
echo.
echo [OK]    %PROJECT_NAME% is running.
echo.
goto show_status

:action_build
call :preflight
echo [INFO]  Force rebuilding Docker images...
docker compose -f %COMPOSE_FILE% build --no-cache
echo [OK]    Build complete.
echo [INFO]  Starting %PROJECT_NAME%...
docker compose -f %COMPOSE_FILE% up -d
echo.
goto show_status

:action_restart
echo [INFO]  Restarting %PROJECT_NAME%...
docker compose -f %COMPOSE_FILE% restart
echo [OK]    Restart complete.
echo.
goto show_status

:action_logs
echo [INFO]  Showing logs (Ctrl+C to exit)...
docker compose -f %COMPOSE_FILE% logs -f
goto end

:action_stop
echo [INFO]  Stopping %PROJECT_NAME%...
docker compose -f %COMPOSE_FILE% down
echo [OK]    All containers stopped.
goto end

:show_status
echo [INFO]  Container status:
docker compose -f %COMPOSE_FILE% ps
echo.
echo [INFO]  Access URL: http://localhost:8000
echo [INFO]  Health check: http://localhost:8000/health
echo [INFO]  API docs: http://localhost:8000/docs
goto end

:usage
echo Usage: deploy.bat [--build] [--restart] [--logs] [--stop]
echo.
echo   --build    Force rebuild images (no cache)
echo   --restart  Restart running containers
echo   --logs     Follow container logs
echo   --stop     Stop all containers
echo   (no flag)  Build + start (default)
exit /b 1

:end
endlocal
