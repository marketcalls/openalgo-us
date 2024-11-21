# OpenAlgo Trading Platform

A modern, open-source algorithmic trading platform for Alpaca Markets, supporting both paper and live trading environments. Built with FastAPI and modern web technologies.

## Features

### Trading Capabilities
- Paper trading support for risk-free strategy testing
- Live trading integration with Alpaca Markets
- Real-time market data processing
- Multiple strategy support
- Performance analytics and reporting

### User Management
- Role-based access control (Super Admin, Admin, User)
- Secure authentication system with JWT
- Google Sign-In integration
- User management interface for administrators
- Profile customization options

### Modern UI/UX
- Clean, modern interface with dark mode support
- Responsive design for all devices
- Real-time data visualization
- Interactive trading dashboard
- DaisyUI components for consistent design

### Technical Features
- FastAPI backend for high performance
- SQLite database for easy setup
- Jinja2 templating engine
- Modern CSS with Tailwind and DaisyUI
- Secure session management

## Tech Stack

- **Backend Framework**: FastAPI
- **Database**: SQLite
- **Frontend**:
  - Tailwind CSS
  - DaisyUI Components
  - Jinja2 Templates
- **Authentication**: 
  - JWT (JSON Web Tokens)
  - Google Sign-In
- **API Integration**: Alpaca Markets API

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git

## Installation

1. Clone the repository:
```bash
git clone https://github.com/marketcalls/openalgo-us.git
cd openalgo-us
```

2. Create and activate a virtual environment:
```bash
# On macOS/Linux
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

1. Copy the example environment file:
```bash
cp .env.sample .env
```

2. Update the .env file with your configuration:
```env
# Application Settings
APP_NAME=OpenAlgo Trading Platform
DEBUG=True
ENVIRONMENT=development

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
DATABASE_URL=sqlite:///./openalgo.db

# Alpaca API Configuration
ALPACA_API_KEY=your-alpaca-api-key
ALPACA_SECRET_KEY=your-alpaca-secret-key
ALPACA_API_BASE_URL=https://paper-api.alpaca.markets
```

## Google Sign-In Setup

1. Create Project in Google Cloud Console:
   ```
   1. Go to console.cloud.google.com
   2. Click "Create Project"
   3. Enter project name
   4. Click "Create"
   ```

2. Configure OAuth Consent Screen:
   ```
   1. Go to "APIs & Services" → "OAuth consent screen"
   2. Select "External" for User Type
   3. Fill required information:
      - App name
      - User support email
      - Application home page: http://127.0.0.1:8000
      - Developer contact email
   4. Add scopes:
      - .../auth/userinfo.email
      - .../auth/userinfo.profile
   5. Add test users for development
   ```

3. Create OAuth Client ID:
   ```
   1. Go to "APIs & Services" → "Credentials"
   2. Click "Create Credentials" → "OAuth client ID"
   3. Select "Web application"
   4. Add JavaScript origins:
      http://127.0.0.1:8000
   5. Add authorized redirect URI:
      http://127.0.0.1:8000/auth/google/callback
   6. Click "Create"
   7. Save Client ID and Secret
   ```

4. Configure in Application:
   ```
   1. Login as super-admin
   2. Go to /manage/auth
   3. Enable Google authentication
   4. Enter Client ID and Secret
   5. Save settings
   ```

Important Notes:
- Save your Client Secret immediately - it won't be shown again
- Add all test users during development
- For production, replace 127.0.0.1:8000 with your domain
- Make sure JavaScript origins match your application URL

## Running the Application

1. Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

2. Access the application:
- Main application: http://127.0.0.1:8000
- API documentation: http://127.0.0.1:8000/docs
- Alternative API docs: http://127.0.0.1:8000/redoc

## User Roles and Permissions

### Super Admin
- Full system access
- Can manage all users and roles
- Access to all platform features
- Can promote/demote other users
- Can configure authentication settings

### Admin
- Can manage regular users
- Access to administrative features
- Cannot modify Super Admin users
- Full trading capabilities

### User
- Basic trading features
- Personal profile management
- View own trading statistics
- Create and manage strategies

## Project Structure

```
openalgo-us/
├── app/
│   ├── routers/
│   │   ├── auth_router.py      # Authentication routes
│   │   ├── user_router.py      # User management
│   │   └── dashboard_router.py # Dashboard and trading
│   ├── templates/
│   │   ├── base.html          # Base template
│   │   ├── index.html         # Landing page
│   │   ├── login.html         # Login page
│   │   ├── register.html      # Registration
│   │   ├── dashboard.html     # Main dashboard
│   │   ├── manage_users.html  # User management
│   │   └── manage_auth.html   # Auth settings
│   ├── static/                # Static assets
│   ├── main.py               # Application entry
│   ├── auth.py              # Authentication logic
│   ├── database.py          # Database setup
│   ├── models.py            # Database models
│   └── schemas.py           # Pydantic schemas
├── .env.sample             # Example environment variables
├── .env                    # Your configuration (not in git)
├── requirements.txt        # Dependencies
└── README.md              # Documentation
```

## Security Features

- JWT-based authentication
- Google Sign-In integration
- Password hashing with bcrypt
- Role-based access control
- Secure cookie handling
- CORS protection
- Input validation
- XSS protection
- Environment-based configuration

## Development

### Setting Up Development Environment

1. Fork the repository
2. Create a new branch for your feature
3. Copy .env.sample to .env and configure
4. Install development dependencies
5. Make your changes
6. Run tests
7. Submit a pull request

### Coding Standards

- Follow PEP 8 guidelines
- Use type hints
- Write docstrings for functions
- Keep functions focused and small
- Comment complex logic

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the AGPL-3.0 License - see the [LICENSE.](LICENSE.md) file for details.

## Support

For support, please open an issue in the GitHub repository or contact the maintainers.
