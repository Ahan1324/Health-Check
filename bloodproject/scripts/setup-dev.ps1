# Blood Analysis App - Development Setup Script (PowerShell)
# This script sets up the development environment for new developers on Windows

param(
    [switch]$SkipDocker
)

Write-Host "🚀 Setting up Blood Analysis App development environment..." -ForegroundColor Green

# Function to print colored output
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Check if we're in the right directory
if (-not (Test-Path "manage.py")) {
    Write-Error "Please run this script from the bloodproject directory"
    exit 1
}

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Success "Python found: $pythonVersion"
} catch {
    Write-Error "Python is not installed. Please install Python 3.11+ first."
    exit 1
}

# Check if Docker is installed
$DockerAvailable = $false
if (-not $SkipDocker) {
    try {
        docker --version | Out-Null
        $DockerAvailable = $true
        Write-Success "Docker is available"
    } catch {
        Write-Warning "Docker is not installed. You'll need to install PostgreSQL manually."
    }
}

# Check if Docker Compose is installed
$DockerComposeAvailable = $false
if ($DockerAvailable) {
    try {
        docker-compose --version | Out-Null
        $DockerComposeAvailable = $true
        Write-Success "Docker Compose is available"
    } catch {
        Write-Warning "Docker Compose is not installed. You'll need to install PostgreSQL manually."
    }
}

# Create virtual environment
Write-Status "Creating virtual environment..."
if (-not (Test-Path "venv")) {
    python -m venv venv
    Write-Success "Virtual environment created"
} else {
    Write-Status "Virtual environment already exists"
}

# Activate virtual environment
Write-Status "Activating virtual environment..."
& "venv\Scripts\Activate.ps1"

# Upgrade pip
Write-Status "Upgrading pip..."
python -m pip install --upgrade pip

# Install dependencies
Write-Status "Installing Python dependencies..."
pip install -r requirements.txt
Write-Success "Dependencies installed"

# Set up environment file
if (-not (Test-Path ".env")) {
    Write-Status "Creating .env file from template..."
    Copy-Item "env.example" ".env"
    Write-Success ".env file created"
    Write-Warning "Please edit .env file with your database credentials"
} else {
    Write-Status ".env file already exists"
}

# Start database
if ($DockerAvailable -and $DockerComposeAvailable) {
    Write-Status "Starting PostgreSQL database with Docker..."
    docker-compose up -d db
    
    # Wait for database to be ready
    Write-Status "Waiting for database to be ready..."
    Start-Sleep -Seconds 10
    
    # Check if database is ready
    try {
        docker-compose exec -T db pg_isready -U postgres | Out-Null
        Write-Success "Database is ready"
    } catch {
        Write-Warning "Database might not be ready yet. Please wait a moment and try again."
    }
} else {
    Write-Warning "Docker not available. Please ensure PostgreSQL is running and accessible."
}

# Run migrations
Write-Status "Running database migrations..."
python manage.py migrate
Write-Success "Migrations completed"

# Import initial data
Write-Status "Importing blood markers..."
python manage.py import_markers_from_brg

Write-Status "Importing clinical conditions..."
python manage.py import_clinical_conditions

Write-Status "Seeding initial data..."
python manage.py seed_initial_data

Write-Success "Initial data imported"

# Create superuser
Write-Status "Creating superuser..."
Write-Host "Please create a superuser account:" -ForegroundColor Yellow
python manage.py createsuperuser

# Collect static files
Write-Status "Collecting static files..."
python manage.py collectstatic --noinput
Write-Success "Static files collected"

# Test the application
Write-Status "Testing application health..."
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health/" -UseBasicParsing -TimeoutSec 5
    Write-Success "Application is running and healthy"
} catch {
    Write-Status "Starting development server for testing..."
    Start-Process python -ArgumentList "manage.py runserver" -WindowStyle Hidden
    $ServerProcess = Get-Process python | Where-Object { $_.ProcessName -eq "python" } | Select-Object -Last 1
    Start-Sleep -Seconds 5
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health/" -UseBasicParsing -TimeoutSec 5
        Write-Success "Application is running and healthy"
    } catch {
        Write-Warning "Could not verify application health. Please check manually."
    }
    
    # Stop the test server
    if ($ServerProcess) {
        Stop-Process -Id $ServerProcess.Id -Force
    }
}

Write-Success "🎉 Development environment setup complete!"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Edit .env file with your database credentials"
Write-Host "2. Run: python manage.py runserver"
Write-Host "3. Visit: http://localhost:8000"
Write-Host "4. Health check: http://localhost:8000/health/"
Write-Host ""
Write-Host "Or use Docker Compose:" -ForegroundColor Yellow
Write-Host "docker-compose up --build"
Write-Host ""
Write-Host "For more information, see SETUP.md and HANDOVER.md" -ForegroundColor Yellow
