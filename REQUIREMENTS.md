# 📦 Package Requirements Guide

## Requirements Files

This project has multiple requirements files for different use cases:

### 🔧 Core Requirements (`requirements-core.txt`)
Essential packages needed to run the basic Django API:
- Django 4.2.7
- Django REST Framework
- JWT Authentication
- CORS Headers
- API Documentation (Swagger)
- Image handling (Pillow)

**Install only core requirements:**
```bash
pip install -r requirements-core.txt
```

### 🚀 Full Requirements (`requirements.txt`)
All packages including optional features:
- Core requirements +
- Social authentication (Google, Facebook)
- Background tasks (Celery, Redis)
- Email services
- Database support (PostgreSQL)
- File storage (AWS S3)
- Security features
- Development tools

**Install full requirements:**
```bash
pip install -r requirements.txt
```

### 🔨 Development Requirements (`requirements-dev.txt`)
Additional packages for development:
- Debug toolbar
- Testing frameworks
- Code formatting tools
- Git hooks

**Install dev requirements:**
```bash
pip install -r requirements-core.txt
pip install -r requirements-dev.txt
```

### 🌐 Production Requirements (`requirements-prod.txt`)
Optimized for production deployment:
- Core requirements +
- Production database support
- Email services
- File storage
- Performance optimization
- Security features
- Monitoring tools

**Install production requirements:**
```bash
pip install -r requirements-prod.txt
```

## 🛠️ Package Details

### Core Django Packages
- `Django==4.2.7` - Main Django framework
- `djangorestframework==3.14.0` - REST API framework
- `django-cors-headers==4.3.1` - CORS support for frontend
- `djangorestframework-simplejwt==5.3.0` - JWT authentication
- `python-decouple==3.8` - Environment variables management

### Authentication & Security
- `django-allauth==0.57.0` - Social authentication
- `cryptography==41.0.7` - Encryption support
- `django-ratelimit==4.1.0` - API rate limiting
- `PyJWT==2.8.0` - JSON Web Tokens

### Database Support
- `psycopg2-binary==2.9.9` - PostgreSQL adapter
- `dj-database-url==2.1.0` - Database URL parsing

### File & Media Handling
- `Pillow==10.1.0` - Image processing
- `boto3==1.34.0` - AWS S3 integration
- `django-storages==1.14.2` - File storage backends

### API Documentation
- `drf-yasg==1.21.7` - Swagger/OpenAPI documentation
- `uritemplate==4.1.1` - URL template support
- `packaging==23.2` - Package version handling

### Background Tasks
- `celery==5.3.4` - Distributed task queue
- `redis==5.0.1` - In-memory data store
- `django-celery-beat==2.5.0` - Periodic tasks

### Email Services
- `django-ses==3.5.2` - Amazon SES email backend
- `requests==2.31.0` - HTTP library

### Development Tools
- `django-debug-toolbar==4.2.0` - Debug information
- `pytest==7.4.4` - Testing framework
- `pytest-django==4.7.0` - Django testing integration
- `black==23.12.1` - Code formatter
- `flake8==7.0.0` - Code linter
- `coverage==7.4.0` - Code coverage

### Performance & Production
- `whitenoise==6.6.0` - Static file serving
- `sentry-sdk==1.39.2` - Error monitoring

## ⚡ Quick Install Commands

### Minimal Setup (Core only)
```bash
pip install -r requirements-core.txt
```

### Full Development Setup
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Production Setup
```bash
pip install -r requirements-prod.txt
```

## 🚨 Troubleshooting

### Common Installation Issues:

1. **Pillow installation fails:**
```bash
# Install system dependencies first (Ubuntu/Debian)
sudo apt-get install libjpeg-dev zlib1g-dev

# Or use conda
conda install pillow
```

2. **psycopg2 installation fails:**
```bash
# Install PostgreSQL development headers
sudo apt-get install postgresql-server-dev-all

# Or use binary version
pip install psycopg2-binary
```

3. **Cryptography installation fails:**
```bash
# Install system dependencies
sudo apt-get install build-essential libssl-dev libffi-dev

# Or use conda
conda install cryptography
```

4. **Redis connection issues:**
```bash
# Install Redis server
sudo apt-get install redis-server

# Or use Docker
docker run -d -p 6379:6379 redis:alpine
```

## 🎯 Recommended Installation Order

1. **Start with core requirements:**
   ```bash
   pip install -r requirements-core.txt
   ```

2. **Test basic functionality:**
   ```bash
   python manage.py runserver
   ```

3. **Add development tools if needed:**
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Add full features when ready:**
   ```bash
   pip install -r requirements.txt
   ```

## 📝 Version Notes

- All package versions are pinned for stability
- Compatible with Python 3.8+
- Tested on Windows, macOS, and Linux
- Update versions carefully in production

---

**Need help? Check the main setup guide in [SETUP.md](SETUP.md)**
