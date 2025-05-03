# ChefGPT - AI Cooking Assistant

An AI-powered cooking assistant that helps users create and manage recipes through natural conversation.

## Setup Instructions

1. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run migrations:
```bash
python manage.py migrate
```

4. Start the development server:
```bash
python manage.py runserver
```

5. Access the application at http://127.0.0.1:8000/

## Project Structure

- `cooking/` - Main application directory
  - `templates/` - HTML templates
  - `static/` - Static files (CSS, JS, images)
  - `models.py` - Database models
  - `views.py` - View functions
  - `urls.py` - URL routing
  - `forms.py` - Form definitions

## Features (Planned)

- User authentication
- AI-powered chat interface
- Dynamic recipe generation
- Recipe book management
- Recipe sharing
- Voice input support 