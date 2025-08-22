#!/bin/bash

# Blood Analysis App - Development Setup Script
# This script sets up the development environment for new developers

set -e

echo "🚀 Setting up Blood Analysis App development environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    print_error "Please run this script from the bloodproject directory"
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.11+ first."
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_warning "Docker is not installed. You'll need to install PostgreSQL manually."
    DOCKER_AVAILABLE=false
else
    DOCKER_AVAILABLE=true
    print_success "Docker is available"
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_warning "Docker Compose is not installed. You'll need to install PostgreSQL manually."
    DOCKER_COMPOSE_AVAILABLE=false
else
    DOCKER_COMPOSE_AVAILABLE=true
    print_success "Docker Compose is available"
fi

# Create virtual environment
print_status "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt
print_success "Dependencies installed"

# Set up environment file
if [ ! -f ".env" ]; then
    print_status "Creating .env file from template..."
    cp env.example .env
    print_success ".env file created"
    print_warning "Please edit .env file with your database credentials"
else
    print_status ".env file already exists"
fi

# Start database
if [ "$DOCKER_AVAILABLE" = true ] && [ "$DOCKER_COMPOSE_AVAILABLE" = true ]; then
    print_status "Starting PostgreSQL database with Docker..."
    docker-compose up -d db
    
    # Wait for database to be ready
    print_status "Waiting for database to be ready..."
    sleep 10
    
    # Check if database is ready
    if docker-compose exec -T db pg_isready -U postgres; then
        print_success "Database is ready"
    else
        print_warning "Database might not be ready yet. Please wait a moment and try again."
    fi
else
    print_warning "Docker not available. Please ensure PostgreSQL is running and accessible."
fi

# Run migrations
print_status "Running database migrations..."
python manage.py migrate
print_success "Migrations completed"

# Import initial data
print_status "Importing blood markers..."
python manage.py import_markers_from_brg

print_status "Importing clinical conditions..."
python manage.py import_clinical_conditions

print_status "Seeding initial data..."
python manage.py seed_initial_data

print_success "Initial data imported"

# Create superuser
print_status "Creating superuser..."
echo "Please create a superuser account:"
python manage.py createsuperuser

# Collect static files
print_status "Collecting static files..."
python manage.py collectstatic --noinput
print_success "Static files collected"

# Test the application
print_status "Testing application health..."
if curl -s http://localhost:8000/health/ > /dev/null 2>&1; then
    print_success "Application is running and healthy"
else
    print_status "Starting development server for testing..."
    python manage.py runserver &
    SERVER_PID=$!
    sleep 5
    
    if curl -s http://localhost:8000/health/ > /dev/null 2>&1; then
        print_success "Application is running and healthy"
    else
        print_warning "Could not verify application health. Please check manually."
    fi
    
    # Stop the test server
    kill $SERVER_PID 2>/dev/null || true
fi

print_success "🎉 Development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your database credentials"
echo "2. Run: python manage.py runserver"
echo "3. Visit: http://localhost:8000"
echo "4. Health check: http://localhost:8000/health/"
echo ""
echo "Or use Docker Compose:"
echo "docker-compose up --build"
echo ""
echo "For more information, see SETUP.md and HANDOVER.md"
