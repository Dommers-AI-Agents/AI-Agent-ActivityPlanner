# AI Group Planner

An AI-powered application for planning group activities based on everyone's preferences. It starts with an SMS invitation and transitions to a web interface for a better user experience.

## Overview

AI Group Planner helps groups coordinate and plan activities by:

1. Collecting preferences from all participants
2. Using AI to generate an optimal activity plan
3. Gathering feedback and refining the plan
4. Notifying everyone of the final details

## Features

- **SMS and Web Integration**: Initial contact via text message with a link to continue on the web
- **Preference Collection**: Ask participants a series of questions in small batches
- **AI-Powered Planning**: Generate personalized activity recommendations based on everyone's input
- **Multi-Channel Communication**: Email for detailed plans, text for quick notifications
- **Responsive Design**: Mobile-friendly web interface for easy access
- **Group Management**: Track participant status and feedback

## Technical Architecture

- **Backend**: Python/Flask
- **Database**: SQLAlchemy with SQLite/PostgreSQL
- **SMS Integration**: Twilio API
- **Email Service**: SendGrid
- **Frontend**: HTML, CSS, JavaScript with Bootstrap

## Installation

### Prerequisites

- Python 3.9+
- PostgreSQL (optional, SQLite for development)
- Twilio account and phone number
- SendGrid account

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ai-planner.git
   cd ai-planner
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file based on the `.env.example`:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration details
   ```

5. Initialize the database:
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

6. Run the application:
   ```bash
   flask run
   ```

## Configuration

The main configuration options in the `.env` file are:

- `FLASK_APP`: Entry point for the Flask application
- `FLASK_ENV`: Environment mode (development, testing, production)
- `SECRET_KEY`: Secret key for session security
- `DATABASE_URL`: Database connection string
- `APP_URL`: Base URL for the application
- `TWILIO_ACCOUNT_SID`: Your Twilio account SID
- `TWILIO_AUTH_TOKEN`: Your Twilio auth token
- `TWILIO_PHONE_NUMBER`: Your Twilio phone number
- `SENDGRID_API_KEY`: Your SendGrid API key
- `DEFAULT_FROM_EMAIL`: Default sender email address

## Project Structure

```
ai-planner/
├── app/
│   ├── __init__.py          # Application factory
│   ├── config.py            # Configuration settings
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py      # Database models
│   │   └── planner.py       # Planning logic
│   ├── services/
│   │   ├── __init__.py
│   │   ├── sms_service.py   # SMS service (Twilio)
│   │   └── email_service.py # Email service (SendGrid)
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css    # Custom CSS
│   │   └── js/
│   │       └── main.js      # Custom JavaScript
│   ├── templates/
│   │   ├── base.html        # Base template
│   │   ├── index.html       # Landing page
│   │   ├── create_activity.html    # Create activity page
│   │   ├── activity_detail.html    # Activity detail page
│   │   ├── questions.html          # Questions interface
│   │   ├── plan.html               # Plan display page
│   │   ├── feedback.html           # Feedback page
│   │   └── emails/                 # Email templates
│   │       ├── welcome.html
│   │       ├── plan.html
│   │       ├── notification.html
│   │       └── feedback.html
│   ├── utils/
│   │   ├── __init__.py
│   │   └── helpers.py       # Utility functions
│   └── views/
│       ├── __init__.py
│       ├── main.py          # Main routes
│       └── api.py           # API endpoints
├── migrations/              # Database migrations
├── tests/                   # Unit and integration tests
├── .env.example             # Example environment variables
├── .gitignore               # Git ignore file
├── main.py                  # Application entry point
├── README.md                # Project documentation
└── requirements.txt         # Python dependencies
```

## Usage

### Creating a New Activity

1. Visit the homepage and click "Create New Activity"
2. Enter your information as the organizer
3. Add participants with their phone numbers and optional email addresses
4. Submit the form to create the activity and send invitations

### Participant Experience

1. Participant receives an SMS with a link to the web interface
2. They answer questions about their preferences in small batches
3. Once all participants have provided input (or enough have), the AI generates a plan
4. Participants receive the plan via email and can provide feedback
5. The final plan is distributed to everyone

## Development

### Adding New Question Types

1. Update the `generate_questions_batch` method in `app/models/planner.py`
2. Add rendering support in `createQuestionElement` function in `app/static/js/main.js`
3. Include handling in the `submitAnswers` function

### Extending the AI Planning Logic

The planning logic is located in `app/models/planner.py`. You can enhance it by:

1. Adding more sophisticated preference analysis
2. Implementing machine learning models for better recommendations
3. Integrating with external APIs for activity suggestions
4. Adding support for location-based planning

## Deployment

### Heroku

```bash
# Install Heroku CLI and login
heroku login

# Create a new Heroku app
heroku create ai-group-planner

# Add PostgreSQL add-on
heroku addons:create heroku-postgresql:hobby-dev

# Configure environment variables
heroku config:set FLASK_ENV=production
heroku config:set SECRET_KEY=your-secret-key
heroku config:set TWILIO_ACCOUNT_SID=your-account-sid
heroku config:set TWILIO_AUTH_TOKEN=your-auth-token
heroku config:set TWILIO_PHONE_NUMBER=your-phone-number
heroku config:set SENDGRID_API_KEY=your-sendgrid-api-key
heroku config:set DEFAULT_FROM_EMAIL=your-email@example.com
heroku config:set APP_URL=https://your-app-name.herokuapp.com

# Push to Heroku
git push heroku main

# Run database migrations
heroku run flask db upgrade
```

### Docker

A `Dockerfile` and `docker-compose.yml` are provided for containerized deployment.

```bash
# Build and run with Docker Compose
docker-compose up -d

# Run migrations
docker-compose exec web flask db upgrade
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Flask](https://flask.palletsprojects.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Twilio](https://www.twilio.com/)
- [SendGrid](https://sendgrid.com/)
- [Bootstrap](https://getbootstrap.com/)
# AI-Agent-ActivityPlanner
