# Changelog

All notable changes to the Blood Analysis Application will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Docker containerization for Google Cloud Run deployment
- Health check endpoint at `/health/`
- Production settings configuration
- Comprehensive deployment documentation
- Development setup scripts for Linux/Mac and Windows
- Project handover documentation
- Environment variable configuration
- Static file serving with WhiteNoise
- Database connection waiting mechanism
- Cloud Build CI/CD configuration

### Changed
- Updated Django to version 5.2.3
- Migrated from SQLite to PostgreSQL for production
- Enhanced security settings for production deployment
- Improved error handling and logging

### Security
- Added non-root user in Docker container
- Implemented proper environment variable handling
- Added security headers and HTTPS configuration
- Generated new SECRET_KEY for production use

## [1.0.0] - 2024-08-22

### Added
- Initial Django application setup
- Blood test result analysis functionality
- Health condition assessment
- AI-powered risk analysis
- Treatment plan recommendations
- User authentication and profiles
- PDF result parsing capability
- Blood marker database with reference ranges
- Clinical conditions database
- Multi-stage analysis workflow
- Asynchronous risk computation
- Sample blood test data

### Features
- Blood test result input (manual and PDF upload)
- Real-time analysis against medical reference ranges
- Health condition identification and risk scoring
- Personalized treatment recommendations
- User progress tracking through analysis stages
- Comprehensive reporting system

### Technical
- Django 5.2.3 framework
- PostgreSQL database backend
- Bootstrap-based responsive UI
- PDF parsing with PyPDF2
- JSON-based data storage for analysis results
- Custom Django management commands for data import
