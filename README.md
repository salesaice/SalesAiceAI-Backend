# Call Center Dashboard Backend

A modern Django REST API backend for a call center/dashboard application with role-based access control, Stripe-powered subscriptions, Twilio call integration, and HomeAI assistance.

## ⚡ Quick Start

### Windows:
```bash
git clone <repository-url>
cd TestRepo
setup.bat
```

### Linux/Mac:
```bash
git clone <repository-url>
cd TestRepo
chmod +x setup.sh
./setup.sh
```

### Manual Setup:
See [SETUP.md](SETUP.md) for detailed instructions.

## 🎯 Features

- **Custom User Model** with email authentication
- **JWT Authentication** with access/refresh tokens
- **Role-based Access Control** (Admin/User roles)
- **Password Reset** via email
- **User Profile Management**
- **Social Authentication** (Google OAuth)
- **API Documentation** with Swagger/ReDoc
- **CORS Support** for frontend integration

## Project Structure

```
├── core/                   # Main project settings
├── accounts/              # User management app
├── authentication/        # Auth endpoints
├── templates/            # Email templates
├── static/              # Static files
├── media/               # User uploaded files
├── requirements.txt     # Python dependencies
├── .env.example        # Environment variables template
└── setup.bat           # Windows setup script
```

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd TestRepo
```

### 2. Windows Setup (Automatic)

```bash
setup.bat
```

### 3. Manual Setup

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Copy environment file
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run server
python manage.py runserver
```

## Environment Variables

Edit `.env` file with your settings:

```env
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Email settings
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# JWT settings
JWT_SECRET_KEY=your-jwt-secret

# Social auth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

## API Endpoints

### Authentication
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login
- `POST /api/auth/logout/` - User logout
- `POST /api/auth/change-password/` - Change password
- `POST /api/auth/password-reset/` - Request password reset
- `POST /api/auth/password-reset-confirm/` - Confirm password reset

### Accounts
- `GET /api/accounts/users/` - List users (Admin only)
- `GET /api/accounts/users/{id}/` - Get user details
- `GET /api/accounts/me/` - Get current user
- `GET/PUT /api/accounts/profile/` - User profile

### Admin
- `/admin/` - Django admin panel

### Documentation
- `/swagger/` - Swagger API documentation
- `/redoc/` - ReDoc API documentation

## Authentication

### JWT Tokens

After login, you'll receive:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

Use the access token in headers:
```
Authorization: Bearer <access_token>
```

### User Roles

- **Admin**: Full access to all endpoints
- **User**: Limited access to own data

## Email Configuration

For password reset emails, configure your email settings in `.env`:

```env
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password  # Use App Password for Gmail
```

## Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add your credentials to `.env`

## Development

### Running Tests
```bash
python manage.py test
```

### Creating Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Collecting Static Files
```bash
python manage.py collectstatic
```

## Deployment

### Production Settings

1. Set `DEBUG=False` in `.env`
2. Configure proper database (PostgreSQL recommended)
3. Set up email backend (SMTP/SES)
4. Configure static file serving
5. Set secure headers

### Environment Variables for Production

```env
DEBUG=False
SECRET_KEY=your-production-secret-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

## License

MIT License
