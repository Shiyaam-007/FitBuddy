# FitBuddy - AI Fitness Plan Generator

FitBuddy is an AI-powered fitness application built with FastAPI and Google Gemini models. It generates personalized 7-day workout plans using Gemini Pro, provides quick nutrition tips using Gemini Flash, and allows users to update their plans based on feedback. The application includes a clean web interface, SQLite database for storage, and an admin dashboard to view all users' plans.

## Features

- **Personalized Workout Plans**: Get a customized 7-day workout schedule based on age, weight, goal, and preferred intensity using Gemini Pro.
- **Nutrition Tips**: Receive quick and relevant nutrition advice powered by Gemini Flash.
- **Feedback-Based Updates**: Iteratively improve and adjust your workout plan by providing feedback.
- **Admin Dashboard**: View all generated user plans and details in a single dashboard.
- **Local Database**: Uses SQLite for persistent storage of user details and their respective plans.

## Tech Stack

- **Backend**: FastAPI, Python 3
- **Database**: SQLite, SQLAlchemy
- **AI Integration**: Google GenAI SDK (Gemini 1.5 Pro & Gemini 1.5 Flash)
- **Frontend**: Jinja2 Templates, HTML, CSS

## Project Structure

```text
fitbuddy/
├── requirements.txt            # Project dependencies
├── app/
│   ├── main.py                 # FastAPI entry point
│   ├── routes.py               # Core route handlers
│   ├── database.py             # SQLAlchemy models and DB logic
│   ├── schemas.py              # Pydantic models for validation
│   ├── gemini_generator.py     # Gemini Pro - workout plan generator
│   ├── gemini_flash_generator.py # Gemini Flash - nutrition tips
│   ├── updated_plan.py         # Feedback-based plan updater
│   ├── nutrition.py            # Handles nutrition-specific logic
│   ├── templates/
│   │   ├── index.html          # User input form
│   │   ├── result.html         # Workout plan, tip, feedback
│   │   └── all_users.html      # Admin dashboard
│   └── static/
│       └── images/
│           └── gym-bg.jpg      # Gym-themed background
└── fitbuddy.db                 # Local SQLite database (auto-generated)
```

## Prerequisites

- Python 3.8+
- A Google API Key from [Google AI Studio](https://aistudio.google.com/app/apikey)

## Installation & Setup

1. **Clone the repository** (if applicable) and navigate to the project directory:
   ```bash
   cd fitbuddy
   ```

2. **Create and activate a virtual environment**:
   - **Windows**:
     ```powershell
     python -m venv venv
     venv\Scripts\activate
     ```
   - **macOS/Linux**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Copy the example environment file and add your Google API Key:
   - **Windows**: `copy .env.example .env`
   - **macOS/Linux**: `cp .env.example .env`
   
   Open the `.env` file and set your key:
   ```env
   GOOGLE_API_KEY="your_api_key_here"
   ```

## Running the Application

Start the FastAPI development server:

```bash
uvicorn app.main:app --reload
```

- **Web Application**: Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.
- **Admin Dashboard**: Open [http://127.0.0.1:8000/users](http://127.0.0.1:8000/users).
- **API Documentation**: Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for the interactive Swagger UI.

## Testing

The project includes tests that use mocked Gemini responses, so no API key is needed to run them.

1. **Install development dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Run tests**:
   ```bash
   pytest -v
   ```
