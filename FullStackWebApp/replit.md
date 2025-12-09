# RoomieMatch - Roommate & Flat Finder Web Application

## Overview
A full-stack web application for finding roommates and flat listings. Built with Flask, SQLite, and TailwindCSS as a beginner-friendly final year project.

## Current State
- **Status**: Complete MVP
- **Last Updated**: December 2024

## Tech Stack
- **Backend**: Python Flask
- **Database**: SQLite with Flask-SQLAlchemy ORM
- **Frontend**: HTML, TailwindCSS (via CDN), Jinja2 Templates
- **Authentication**: Werkzeug password hashing
- **Image Processing**: Pillow

## Project Structure
```
project/
├── app.py                    # Main Flask application
├── replit.md                 # Project documentation
├── .gitignore                # Git ignore file
│
├── static/
│   ├── css/                  # Custom CSS (if needed)
│   ├── uploads/              # User uploaded images
│   └── js/                   # Custom JavaScript (if needed)
│
├── templates/
│   ├── base.html             # Base template with navbar/footer
│   ├── home.html             # Landing page
│   ├── login.html            # Login page
│   ├── register.html         # Registration page
│   ├── dashboard.html        # User dashboard
│   ├── profile.html          # User profile page
│   ├── post_listing.html     # Create listing page
│   ├── browse_listings.html  # Browse all listings
│   ├── browse_roommates.html # Browse potential roommates
│   ├── view_listing.html     # Single listing detail page
│   └── view_roommate.html    # Single roommate profile page
│
└── instance/
    └── database.db           # SQLite database (auto-generated)
```

## Features

### 1. User Authentication
- Registration with email/password
- Password hashing using Werkzeug
- Session-based login system

### 2. User Profiles
- Personal details (name, age, gender)
- Budget preferences
- Preferred locations (comma-separated)
- Lifestyle tags (comma-separated)
- Profile image upload

### 3. Flat Listings
- Create listings with title, location, rent, room type
- Upload up to 2 images
- Add amenities
- Browse with filters (location, rent range, room type)

### 4. Roommate Matching
- Browse other users looking for roommates
- Filter by location and budget
- **Simple Compatibility Scoring System:**
  ```
  score = (location_match * 5) + (budget_closeness * 3) + (lifestyle_match * 2)
  Maximum: 10 points
  ```

## How to Run
The application automatically runs on port 5000. The database and sample data are created on first run.

## Demo Accounts
Pre-populated for testing:
- **Email**: alex@example.com | **Password**: password123
- **Email**: priya@example.com | **Password**: password123
- (and more sample users)

## Where to Edit

### Templates
All HTML templates are in the `/templates` folder:
- Edit `base.html` for navbar/footer changes
- Edit individual page templates for specific pages

### Matching Logic
The compatibility algorithm is in `app.py`, function `calculate_compatibility()`:
```python
def calculate_compatibility(user1, user2):
    # Location Match: up to 5 points
    # Budget Closeness: up to 3 points
    # Lifestyle Match: up to 2 points
    return score  # 0 to 10
```

### Styling
- Uses TailwindCSS via CDN
- Custom styles are in `base.html` <style> block
- Color scheme uses primary (blue) and accent (rose) colors

## User Preferences
- Modern, Airbnb-inspired UI
- Beginner-friendly code with comments
- Mobile responsive design
- No complex JavaScript - Tailwind CSS animations only

## Recent Changes
- Initial project creation with all features
- Added sample data for 6 users and 8 listings
- Implemented compatibility scoring system
