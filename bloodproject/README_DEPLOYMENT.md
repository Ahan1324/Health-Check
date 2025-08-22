# Blood Analysis App - Google Cloud Run Deployment Guide

This guide will help you deploy the Blood Analysis Django application to Google Cloud Run.

## Prerequisites

1. **Google Cloud Account**: You need a Google Cloud account with billing enabled
2. **Google Cloud CLI**: Install the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
3. **Docker**: Install [Docker](https://docs.docker.com/get-docker/)
4. **PostgreSQL Database**: You'll need a PostgreSQL database (Cloud SQL recommended)

## Setup Steps

### 1. Initialize Google Cloud Project

```bash
# Login to Google Cloud
gcloud auth login

# Create a new project (or use existing)
gcloud projects create your-project-id --name="Blood Analysis App"

# Set the project
gcloud config set project your-project-id

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### 2. Set Up PostgreSQL Database (Cloud SQL)

```bash
# Create a Cloud SQL instance
gcloud sql instances create blood-analysis-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=us-central1 \
    --root-password=jOHNcENA123!

# Create the database
gcloud sql databases create blooddb --instance=blood-analysis-db

# Create a user
gcloud sql users create blooduser --instance=blood-analysis-db --password=jOHNcENA123!
```

### 3. Configure Environment Variables

Set the following environment variables in your shell:

```bash
export PROJECT_ID="your-project-id"
export DB_HOST="your-db-connection-string"
export DB_NAME="blooddb"
export DB_USER="blooduser"
export DB_PASSWORD="jOHNcENA123!"
```

### 4. Deploy the Application

#### Option A: Using the deployment script

```bash
# Make the script executable
chmod +x deploy.sh

# Update the PROJECT_ID in deploy.sh
# Then run the deployment
./deploy.sh
```

#### Option B: Manual deployment

```bash
# Build the Docker image
docker build -t gcr.io/$PROJECT_ID/blood-analysis-app .

# Push to Container Registry
docker push gcr.io/$PROJECT_ID/blood-analysis-app

# Deploy to Cloud Run
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

#### Option C: Using Cloud Build (CI/CD)

```bash
# Submit the build
gcloud builds submit --config cloudbuild.yaml .
```

### 5. Run Database Migrations

After deployment, you may need to run migrations:

```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe blood-analysis-app --region=us-central1 --format='value(status.url)')

# Run migrations (you'll need to create a management command or use Cloud Run jobs)
```

## Local Development

For local development, use Docker Compose:

```bash
# Start the services
docker-compose up --build

# The application will be available at http://localhost:8000
```

## Environment Variables

The following environment variables can be configured:

- `DEBUG`: Set to `False` in production
- `SECRET_KEY`: Django secret key (generate a new one for production)
- `DB_HOST`: PostgreSQL database host
- `DB_NAME`: Database name
- `DB_USER`: Database username
- `DB_PASSWORD`: Database password
- `DB_PORT`: Database port (default: 5432)

## Security Considerations

1. **Generate a new SECRET_KEY** for production
2. **Use strong database passwords**
3. **Configure ALLOWED_HOSTS** properly
4. **Enable HTTPS** in production
5. **Set up proper IAM permissions**

## Monitoring and Logging

```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=blood-analysis-app" --limit=50

# Monitor the service
gcloud run services describe blood-analysis-app --region=us-central1
```

## Troubleshooting

### Common Issues

1. **Database Connection**: Ensure the database is accessible from Cloud Run
2. **Static Files**: Check if static files are being served correctly
3. **Memory Issues**: Increase memory allocation if needed
4. **Timeout Issues**: Adjust the timeout settings

### Useful Commands

```bash
# Check service status
gcloud run services list

# View service logs
gcloud run services logs read blood-analysis-app --region=us-central1

# Update environment variables
gcloud run services update blood-analysis-app \
    --region=us-central1 \
    --set-env-vars DEBUG=False

# Scale the service
gcloud run services update blood-analysis-app \
    --region=us-central1 \
    --max-instances=20
```

## Cost Optimization

1. **Set appropriate max instances** to control costs
2. **Use Cloud SQL Proxy** for database connections
3. **Monitor usage** in Google Cloud Console
4. **Set up billing alerts**

## Next Steps

1. Set up a custom domain
2. Configure SSL certificates
3. Set up monitoring and alerting
4. Implement CI/CD pipeline
5. Add health checks
6. Set up backup strategies
