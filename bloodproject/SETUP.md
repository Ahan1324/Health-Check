# Blood Analysis App - Developer Setup Guide

This guide is for new developers taking over the Blood Analysis Django application.

## 🚀 Quick Start for New Developers

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- PostgreSQL (or use Docker)
- Git

### 1. Clone and Setup
```bash
git clone <repository-url>
cd bloodproject
```

### 2. Environment Setup
```bash
# Copy environment template
cp env.example .env

# Edit .env with your local settings
# For local development, you can use:
DEBUG=True
DB_HOST=localhost
DB_NAME=blooddb
DB_USER=postgres
DB_PASSWORD=your_password
```

### 3. Database Setup
```bash
# Option A: Using Docker Compose (Recommended)
docker-compose up -d db
# Wait for database to be ready, then:
python manage.py migrate

# Option B: Local PostgreSQL
# Install PostgreSQL and create database
createdb blooddb
python manage.py migrate
```

### 4. Install Dependencies
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Load Initial Data
```bash
# Run the data import commands
python manage.py import_markers_from_brg
python manage.py import_clinical_conditions
python manage.py seed_initial_data
```

### 6. Create Superuser
```bash
python manage.py createsuperuser
```

### 7. Run the Application
```bash
# Development server
python manage.py runserver

# Or using Docker Compose
docker-compose up --build
```

## 📁 Project Structure Overview

```
bloodproject/
├── bloodapp/                    # Main Django application
│   ├── management/commands/     # Custom management commands
│   │   ├── import_markers_from_brg.py      # Import blood markers
│   │   ├── import_clinical_conditions.py   # Import health conditions
│   │   ├── seed_initial_data.py            # Seed initial data
│   │   └── wait_for_db.py                  # Database connection check
│   ├── models.py               # Database models
│   ├── views.py                # View functions
│   ├── forms.py                # Django forms
│   ├── utils.py                # Utility functions
│   └── urls.py                 # URL routing
├── bloodproject/               # Django project settings
│   ├── settings.py             # Development settings
│   ├── settings_production.py  # Production settings
│   └── urls.py                 # Main URL configuration
├── templates/                  # HTML templates
├── blood_data/                 # Sample blood test data
├── Dockerfile                  # Docker configuration
├── docker-compose.yml          # Local development setup
├── requirements.txt            # Python dependencies
├── deploy.sh                   # Deployment script
└── cloudbuild.yaml            # Cloud Build configuration
```

## 🔧 Key Components

### Data Models
- **Marker**: Blood test markers with reference ranges
- **HealthCondition**: Health conditions and their markers
- **PatientProfile**: User profiles and analysis stages
- **AIAnalysisResult**: AI analysis results storage
- **RiskComputationTask**: Async risk computation tasks

### Management Commands
- `import_markers_from_brg`: Imports blood markers from CSV
- `import_clinical_conditions`: Imports health conditions
- `seed_initial_data`: Seeds initial application data
- `wait_for_db`: Waits for database connection

### Key Features
- Blood test result analysis
- Health condition assessment
- AI-powered risk analysis
- Treatment plan recommendations
- PDF result parsing
- User authentication and profiles

## 🐳 Docker Development

### Using Docker Compose
```bash
# Start all services
docker-compose up --build

# Start only database
docker-compose up -d db

# Run migrations in container
docker-compose exec web python manage.py migrate

# Create superuser in container
docker-compose exec web python manage.py createsuperuser
```

### Testing Docker Build
```bash
# Test the Docker build locally
./test-docker.sh
```

## 🚀 Deployment

### Local Testing
```bash
# Test production build locally
docker build -t blood-analysis-app .
docker run -p 8000:8080 -e DEBUG=False blood-analysis-app
```

### Google Cloud Run Deployment
See `README_DEPLOYMENT.md` for detailed deployment instructions.

## 🔍 Troubleshooting

### Common Issues

1. **Database Connection**
   ```bash
   # Check if database is running
   docker-compose ps
   
   # Check database logs
   docker-compose logs db
   ```

2. **Migration Issues**
   ```bash
   # Reset migrations (if needed)
   python manage.py migrate --fake-initial
   
   # Show migration status
   python manage.py showmigrations
   ```

3. **Static Files**
   ```bash
   # Collect static files
   python manage.py collectstatic
   ```

4. **Docker Issues**
   ```bash
   # Clean up Docker
   docker-compose down -v
   docker system prune
   ```

### Health Check
```bash
# Check application health
curl http://localhost:8000/health/
```

## 📊 Data Management

### Importing Data
```bash
# Import blood markers
python manage.py import_markers_from_brg

# Import health conditions
python manage.py import_clinical_conditions

# Seed initial data
python manage.py seed_initial_data
```

### Backup and Restore
```bash
# Backup database
python manage.py dumpdata > backup.json

# Restore database
python manage.py loaddata backup.json
```

## 🔐 Security Notes

- Change default passwords in production
- Generate new SECRET_KEY for production
- Configure ALLOWED_HOSTS properly
- Use environment variables for sensitive data
- Enable HTTPS in production

## 📝 Development Workflow

1. **Feature Development**
   ```bash
   git checkout -b feature/new-feature
   # Make changes
   python manage.py test
   git commit -m "Add new feature"
   ```

2. **Testing**
   ```bash
   # Run tests
   python manage.py test
   
   # Run with coverage
   coverage run --source='.' manage.py test
   coverage report
   ```

3. **Code Quality**
   ```bash
   # Format code
   black .
   
   # Lint code
   flake8 .
   ```

## 📞 Support

- Check existing issues in the repository
- Review `README.md` and `README_DEPLOYMENT.md`
- Contact the previous developer for domain-specific questions
- Check Django documentation for general questions

## 🎯 Next Steps

1. Familiarize yourself with the codebase
2. Set up your development environment
3. Run the application locally
4. Review the deployment documentation
5. Set up monitoring and logging
6. Plan any necessary updates or improvements
