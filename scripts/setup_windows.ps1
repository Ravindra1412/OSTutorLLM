# =============================================================================
# scripts/setup_windows.ps1 — Part 3.12, Section 3 (Local Windows deployment)
#
# Run from PowerShell in the project root:
#   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
# =============================================================================

Write-Host "== OSTutorLLM - Windows Setup ==" -ForegroundColor Cyan

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "Python not found. Install Python 3.12+ from https://www.python.org/downloads/ first." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv venv
}

Write-Host "Activating virtual environment..."
& .\venv\Scripts\Activate.ps1

Write-Host "Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example..."
    Copy-Item ".env.example" ".env"
    $secret = python -c "import secrets; print(secrets.token_hex(32))"
    (Get-Content ".env") -replace "change-this-to-a-long-random-value", $secret | Set-Content ".env"
    Write-Host "Generated a real SECRET_KEY in .env."
}

Write-Host "Running database migrations..."
$env:FLASK_APP = "run.py"
flask db upgrade

$seed = Read-Host "Seed sample data (topics, lessons, demo users)? [y/N]"
if ($seed -eq "y" -or $seed -eq "Y") {
    flask seed-db
}

Write-Host ""
Write-Host "== Setup complete ==" -ForegroundColor Green
Write-Host "Start the server with:"
Write-Host "  .\venv\Scripts\Activate.ps1 ; python run.py"
Write-Host "Then open http://localhost:5000"
