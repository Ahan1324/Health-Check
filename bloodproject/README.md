# Blood Analysis Application

A Django-based web application for analyzing blood test results and providing health insights.

## Features

- Blood test result analysis
- Health condition assessment
- AI-powered risk analysis
- Treatment plan recommendations
- User authentication and profiles
- PDF result parsing

## Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd bloodproject
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up database**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

5. **Run the development server**
   ```bash
   python manage.py runserver
   ```

### Using Docker Compose (Recommended)

1. **Start the application with PostgreSQL**
   ```bash
   docker-compose up --build
   ```

2. **Access the application**
   - Web app: http://localhost:8000
   - Health check: http://localhost:8000/health/

## Deployment to Google Cloud Run

### Prerequisites

- Google Cloud account with billing enabled
- Google Cloud CLI installed
- Docker installed
- PostgreSQL database (Cloud SQL recommended)

### Quick Deployment

1. **Update configuration**
   ```bash
   # Edit deploy.sh and set your PROJECT_ID
   # Set environment variables
   export PROJECT_ID="your-project-id"
   export DB_HOST="your-db-connection-string"
   export DB_NAME="blooddb"
   export DB_USER="your-db-user"
   export DB_PASSWORD="your-db-password"
   ```

2. **Deploy**
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

### Manual Deployment

1. **Build and push Docker image**
   ```bash
   docker build -t gcr.io/$PROJECT_ID/blood-analysis-app .
   docker push gcr.io/$PROJECT_ID/blood-analysis-app
   ```

2. **Deploy to Cloud Run**
   ```bash
   gcloud run deploy blood-analysis-app \
       --image gcr.io/$PROJECT_ID/blood-analysis-app \
       --region us-central1 \
       --platform managed \
       --allow-unauthenticated \
       --memory 512Mi \
       --cpu 1 \
       --max-instances 10 \
       --set-env-vars DEBUG=False \
       --set-env-vars DB_HOST=$DB_HOST \
       --set-env-vars DB_NAME=$DB_NAME \
       --set-env-vars DB_USER=$DB_USER \
       --set-env-vars DB_PASSWORD=$DB_PASSWORD
   ```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Django debug mode | `False` |
| `SECRET_KEY` | Django secret key | Auto-generated |
| `DB_HOST` | Database host | `localhost` |
| `DB_NAME` | Database name | `blooddb` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | Required |
| `DB_PORT` | Database port | `5432` |

## Project Structure

```
bloodproject/
├── bloodapp/                 # Main Django app
│   ├── management/          # Custom management commands
│   ├── migrations/          # Database migrations
│   ├── models.py           # Database models
│   ├── views.py            # View functions
│   └── urls.py             # URL routing
├── bloodproject/           # Django project settings
│   ├── settings.py         # Development settings
│   ├── settings_production.py  # Production settings
│   └── urls.py             # Main URL configuration
├── templates/              # HTML templates
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Local development setup
├── requirements.txt        # Python dependencies
├── deploy.sh              # Deployment script
└── cloudbuild.yaml        # Cloud Build configuration
```

## API Endpoints

- `GET /health/` - Health check endpoint
- `GET /` - Home page
- `GET /login/` - Login page
- `GET /signup/` - Signup page
- `GET /patient-info/` - Patient information form
- `GET /health-concerns/` - Health concerns assessment
- `GET /treatment-plans/` - Treatment plans
- `GET /completed/` - Analysis completed

## Health Check

The application includes a health check endpoint at `/health/` that verifies:
- Application status
- Database connectivity
- Timestamp

## Monitoring

### View Logs
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=blood-analysis-app" --limit=50
```

### Check Service Status
```bash
gcloud run services describe blood-analysis-app --region=us-central1
```

## Troubleshooting

### Common Issues

1. **Database Connection**
   - Ensure database is accessible from Cloud Run
   - Check firewall rules and network configuration
   - Verify connection string format

2. **Static Files**
   - Static files are served by WhiteNoise
   - Ensure `collectstatic` runs during deployment

3. **Memory Issues**
   - Increase memory allocation if needed
   - Monitor resource usage in Cloud Console

### Useful Commands

```bash
# Test Docker build locally
./test-docker.sh

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Check service logs
gcloud run services logs read blood-analysis-app --region=us-central1
```

## Security Considerations

- Generate a new `SECRET_KEY` for production
- Use strong database passwords
- Configure `ALLOWED_HOSTS` properly
- Enable HTTPS in production
- Set up proper IAM permissions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions, please refer to the deployment guide in `README_DEPLOYMENT.md` or create an issue in the repository.
