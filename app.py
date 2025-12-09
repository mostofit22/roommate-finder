"""
=============================================================================
ROOMMATE & FLAT FINDER WEB APPLICATION
=============================================================================
A beginner-friendly Flask application for finding roommates and flat listings.
Features user authentication, listing management, and compatibility matching.

Author: Final Year Project
Tech Stack: Flask, SQLite, TailwindCSS, Jinja2
=============================================================================
"""

import os
import secrets
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image

# =============================================================================
# APP CONFIGURATION
# =============================================================================

app = Flask(__name__)

# Secret key for session management (uses environment variable for security)
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', secrets.token_hex(16))

# Database configuration - using SQLite for simplicity
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# File upload configuration
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Initialize database
db = SQLAlchemy(app)

# =============================================================================
# DATABASE MODELS
# =============================================================================

class User(db.Model):
    """
    User model - stores all user information including profile details.
    
    Attributes:
        id: Unique identifier for each user
        email: User's email address (used for login)
        password_hash: Securely hashed password
        name: User's display name
        age: User's age
        gender: User's gender
        budget: Maximum monthly rent budget
        preferred_locations: Comma-separated list of preferred cities/areas
        lifestyle: Comma-separated lifestyle preferences (e.g., "non-smoker,early-riser")
        bio: Short description about the user
        profile_image: Path to user's profile picture
        created_at: Account creation timestamp
    """
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    budget = db.Column(db.Integer, nullable=True)  # Monthly budget in currency
    preferred_locations = db.Column(db.String(500), nullable=True)  # Comma-separated
    lifestyle = db.Column(db.String(500), nullable=True)  # Comma-separated tags
    bio = db.Column(db.Text, nullable=True)
    profile_image = db.Column(db.String(200), default='default_avatar.png')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship: A user can have multiple listings
    listings = db.relationship('Listing', backref='owner', lazy=True)
    
    def set_password(self, password):
        """Hash and store the user's password securely."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify if the provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)
    
    def get_lifestyle_list(self):
        """Return lifestyle preferences as a list."""
        if self.lifestyle:
            return [tag.strip() for tag in self.lifestyle.split(',')]
        return []
    
    def get_locations_list(self):
        """Return preferred locations as a list."""
        if self.preferred_locations:
            return [loc.strip() for loc in self.preferred_locations.split(',')]
        return []


class Listing(db.Model):
    """
    Listing model - stores flat/room listing information.
    
    Attributes:
        id: Unique identifier for each listing
        user_id: ID of the user who posted the listing
        title: Listing title
        location: City/area where the property is located
        rent: Monthly rent amount
        room_type: Type of room (Private Room, Shared Room, Entire Flat)
        description: Detailed description of the listing
        image1: Path to first image
        image2: Path to second image (optional)
        amenities: Comma-separated list of amenities
        available_from: Date when the room becomes available
        created_at: Listing creation timestamp
        is_active: Whether the listing is currently active
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    rent = db.Column(db.Integer, nullable=False)
    room_type = db.Column(db.String(50), nullable=False)  # Private Room, Shared Room, Entire Flat
    description = db.Column(db.Text, nullable=True)
    image1 = db.Column(db.String(200), default='default_listing.jpg')
    image2 = db.Column(db.String(200), nullable=True)
    amenities = db.Column(db.String(500), nullable=True)  # Comma-separated
    available_from = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def get_amenities_list(self):
        """Return amenities as a list."""
        if self.amenities:
            return [a.strip() for a in self.amenities.split(',')]
        return []


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def allowed_file(filename):
    """
    Check if the uploaded file has an allowed extension.
    
    Args:
        filename: Name of the uploaded file
    
    Returns:
        Boolean indicating if the file type is allowed
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(file, prefix='listing'):
    """
    Save an uploaded image file with a unique name.
    
    Args:
        file: The uploaded file object
        prefix: Prefix for the filename (e.g., 'listing', 'profile')
    
    Returns:
        The filename of the saved image, or None if save failed
    """
    if file and allowed_file(file.filename):
        # Generate a unique filename
        filename = secure_filename(file.filename)
        unique_name = f"{prefix}_{secrets.token_hex(8)}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        
        # Save and optionally resize the image
        try:
            image = Image.open(file)
            # Resize large images to save space (max 1200px width)
            if image.width > 1200:
                ratio = 1200 / image.width
                new_height = int(image.height * ratio)
                image = image.resize((1200, new_height), Image.Resampling.LANCZOS)
            
            # Convert to RGB if necessary (for JPEG compatibility)
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')
            
            image.save(filepath, quality=85, optimize=True)
            return unique_name
        except Exception as e:
            print(f"Error saving image: {e}")
            return None
    return None


def login_required(f):
    """
    Decorator to protect routes that require authentication.
    
    Usage:
        @app.route('/protected')
        @login_required
        def protected_route():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """
    Get the currently logged-in user from the database.
    
    Returns:
        User object if logged in, None otherwise
    """
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None


def calculate_compatibility(user1, user2):
    """
    Calculate compatibility score between two users.
    
    Formula: score = (location_match * 5) + (budget_closeness * 3) + (lifestyle_match * 2)
    Maximum score: 10
    
    Args:
        user1: First user object
        user2: Second user object
    
    Returns:
        Compatibility score from 0 to 10
    """
    score = 0
    
    # Location Match (0 to 5 points)
    # Check if any preferred locations overlap
    locations1 = set([loc.lower() for loc in user1.get_locations_list()])
    locations2 = set([loc.lower() for loc in user2.get_locations_list()])
    
    if locations1 and locations2:
        common_locations = locations1.intersection(locations2)
        if common_locations:
            # More common locations = higher score (max 5 points)
            location_score = min(len(common_locations) * 2.5, 5)
            score += location_score
    
    # Budget Closeness (0 to 3 points)
    # The closer the budgets, the higher the score
    if user1.budget and user2.budget:
        budget_diff = abs(user1.budget - user2.budget)
        max_budget = max(user1.budget, user2.budget)
        if max_budget > 0:
            # Calculate percentage difference
            diff_percent = budget_diff / max_budget
            # Convert to score (0% diff = 3 points, 100% diff = 0 points)
            budget_score = max(0, 3 * (1 - diff_percent))
            score += budget_score
    
    # Lifestyle Match (0 to 2 points)
    # Check how many lifestyle preferences match
    lifestyle1 = set([tag.lower() for tag in user1.get_lifestyle_list()])
    lifestyle2 = set([tag.lower() for tag in user2.get_lifestyle_list()])
    
    if lifestyle1 and lifestyle2:
        common_lifestyle = lifestyle1.intersection(lifestyle2)
        total_lifestyle = lifestyle1.union(lifestyle2)
        if total_lifestyle:
            # Jaccard similarity for lifestyle match
            lifestyle_score = (len(common_lifestyle) / len(total_lifestyle)) * 2
            score += lifestyle_score
    
    # Round to 1 decimal place and ensure max is 10
    return round(min(score, 10), 1)


# =============================================================================
# CONTEXT PROCESSOR - Makes user available in all templates
# =============================================================================

@app.context_processor
def inject_user():
    """Make current user available in all templates."""
    return dict(current_user=get_current_user())


# =============================================================================
# ROUTES - HOME & AUTHENTICATION
# =============================================================================

@app.route('/')
def home():
    """
    Home page route - displays the landing page with hero section.
    Shows featured listings and call-to-action buttons.
    """
    # Get a few recent listings to display on home page
    featured_listings = Listing.query.filter_by(is_active=True)\
                               .order_by(Listing.created_at.desc())\
                               .limit(6).all()
    return render_template('home.html', listings=featured_listings)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    User registration route.
    GET: Display the registration form
    POST: Process the registration and create a new user
    """
    if request.method == 'POST':
        # Get form data
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        name = request.form.get('name', '').strip()
        age = request.form.get('age', type=int)
        gender = request.form.get('gender', '')
        budget = request.form.get('budget', type=int)
        preferred_locations = request.form.get('preferred_locations', '').strip()
        lifestyle = request.form.get('lifestyle', '').strip()
        bio = request.form.get('bio', '').strip()
        
        # Validation
        errors = []
        
        if not email or '@' not in email:
            errors.append('Please enter a valid email address.')
        
        if len(password) < 6:
            errors.append('Password must be at least 6 characters long.')
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        if not name:
            errors.append('Please enter your name.')
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            errors.append('An account with this email already exists.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('register.html')
        
        # Create new user
        user = User(
            email=email,
            name=name,
            age=age,
            gender=gender,
            budget=budget,
            preferred_locations=preferred_locations,
            lifestyle=lifestyle,
            bio=bio
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    User login route.
    GET: Display the login form
    POST: Authenticate user and create session
    """
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            # Create session
            session['user_id'] = user.id
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Log out the current user by clearing the session."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))


# =============================================================================
# ROUTES - DASHBOARD & PROFILE
# =============================================================================

@app.route('/dashboard')
@login_required
def dashboard():
    """
    User dashboard - main hub after login.
    Shows navigation cards to different features.
    """
    user = get_current_user()
    # Get user's own listings
    my_listings = Listing.query.filter_by(user_id=user.id)\
                         .order_by(Listing.created_at.desc()).all()
    return render_template('dashboard.html', user=user, my_listings=my_listings)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """
    User profile page - view and edit profile information.
    GET: Display profile with current information
    POST: Update profile information
    """
    user = get_current_user()
    
    if request.method == 'POST':
        # Update user information
        user.name = request.form.get('name', user.name).strip()
        user.age = request.form.get('age', type=int)
        user.gender = request.form.get('gender', '')
        user.budget = request.form.get('budget', type=int)
        user.preferred_locations = request.form.get('preferred_locations', '').strip()
        user.lifestyle = request.form.get('lifestyle', '').strip()
        user.bio = request.form.get('bio', '').strip()
        
        # Handle profile image upload
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file.filename:
                saved_filename = save_image(file, prefix='profile')
                if saved_filename:
                    user.profile_image = saved_filename
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile.html', user=user)


# =============================================================================
# ROUTES - LISTINGS
# =============================================================================

@app.route('/post-listing', methods=['GET', 'POST'])
@login_required
def post_listing():
    """
    Create a new flat/room listing.
    GET: Display the listing form
    POST: Create the listing with uploaded images
    """
    if request.method == 'POST':
        user = get_current_user()
        
        # Get form data
        title = request.form.get('title', '').strip()
        location = request.form.get('location', '').strip()
        rent = request.form.get('rent', type=int)
        room_type = request.form.get('room_type', '')
        description = request.form.get('description', '').strip()
        amenities = request.form.get('amenities', '').strip()
        
        # Validation
        if not title or not location or not rent:
            flash('Please fill in all required fields.', 'error')
            return render_template('post_listing.html')
        
        # Create listing
        listing = Listing(
            user_id=user.id,
            title=title,
            location=location,
            rent=rent,
            room_type=room_type,
            description=description,
            amenities=amenities
        )
        
        # Handle image uploads
        if 'image1' in request.files:
            file1 = request.files['image1']
            if file1.filename:
                saved_filename = save_image(file1, prefix='listing')
                if saved_filename:
                    listing.image1 = saved_filename
        
        if 'image2' in request.files:
            file2 = request.files['image2']
            if file2.filename:
                saved_filename = save_image(file2, prefix='listing')
                if saved_filename:
                    listing.image2 = saved_filename
        
        db.session.add(listing)
        db.session.commit()
        
        flash('Listing created successfully!', 'success')
        return redirect(url_for('browse_listings'))
    
    return render_template('post_listing.html')


@app.route('/browse-listings')
def browse_listings():
    """
    Browse all available flat/room listings.
    Supports filtering by location and rent range.
    """
    # Get filter parameters
    location = request.args.get('location', '').strip()
    min_rent = request.args.get('min_rent', type=int)
    max_rent = request.args.get('max_rent', type=int)
    room_type = request.args.get('room_type', '')
    
    # Build query
    query = Listing.query.filter_by(is_active=True)
    
    if location:
        query = query.filter(Listing.location.ilike(f'%{location}%'))
    
    if min_rent:
        query = query.filter(Listing.rent >= min_rent)
    
    if max_rent:
        query = query.filter(Listing.rent <= max_rent)
    
    if room_type:
        query = query.filter(Listing.room_type == room_type)
    
    listings = query.order_by(Listing.created_at.desc()).all()
    
    # Get unique locations for filter dropdown
    all_locations = db.session.query(Listing.location).distinct().all()
    locations_list = [loc[0] for loc in all_locations]
    
    return render_template('browse_listings.html', 
                          listings=listings, 
                          locations=locations_list,
                          filters={'location': location, 'min_rent': min_rent, 
                                  'max_rent': max_rent, 'room_type': room_type})


@app.route('/listing/<int:listing_id>')
def view_listing(listing_id):
    """View details of a specific listing."""
    listing = Listing.query.get_or_404(listing_id)
    return render_template('view_listing.html', listing=listing)


@app.route('/delete-listing/<int:listing_id>', methods=['POST'])
@login_required
def delete_listing(listing_id):
    """Delete a listing (only by the owner)."""
    user = get_current_user()
    listing = Listing.query.get_or_404(listing_id)
    
    if listing.user_id != user.id:
        flash('You can only delete your own listings.', 'error')
        return redirect(url_for('dashboard'))
    
    db.session.delete(listing)
    db.session.commit()
    flash('Listing deleted successfully.', 'success')
    return redirect(url_for('dashboard'))


# =============================================================================
# ROUTES - ROOMMATES
# =============================================================================

@app.route('/browse-roommates')
def browse_roommates():
    """
    Browse potential roommates (other users).
    Supports filtering and shows compatibility scores.
    """
    # Get filter parameters
    location = request.args.get('location', '').strip()
    min_budget = request.args.get('min_budget', type=int)
    max_budget = request.args.get('max_budget', type=int)
    
    # Build query (exclude current user if logged in)
    query = User.query
    
    current_user = get_current_user()
    if current_user:
        query = query.filter(User.id != current_user.id)
    
    if location:
        query = query.filter(User.preferred_locations.ilike(f'%{location}%'))
    
    if min_budget:
        query = query.filter(User.budget >= min_budget)
    
    if max_budget:
        query = query.filter(User.budget <= max_budget)
    
    users = query.order_by(User.created_at.desc()).all()
    
    # Calculate compatibility scores for each user
    roommates_with_scores = []
    for user in users:
        score = 0
        if current_user:
            score = calculate_compatibility(current_user, user)
        roommates_with_scores.append({
            'user': user,
            'score': score
        })
    
    # Sort by compatibility score (highest first) if logged in
    if current_user:
        roommates_with_scores.sort(key=lambda x: x['score'], reverse=True)
    
    # Get unique locations for filter dropdown
    all_users_locations = []
    for u in User.query.all():
        all_users_locations.extend(u.get_locations_list())
    unique_locations = list(set(all_users_locations))
    
    return render_template('browse_roommates.html', 
                          roommates=roommates_with_scores,
                          locations=unique_locations,
                          filters={'location': location, 'min_budget': min_budget, 
                                  'max_budget': max_budget})


@app.route('/roommate/<int:user_id>')
def view_roommate(user_id):
    """View detailed profile of a potential roommate."""
    user = User.query.get_or_404(user_id)
    current_user = get_current_user()
    
    # Calculate compatibility if logged in
    score = 0
    if current_user and current_user.id != user_id:
        score = calculate_compatibility(current_user, user)
    
    return render_template('view_roommate.html', roommate=user, score=score)


# =============================================================================
# INITIALIZE DATABASE & CREATE SAMPLE DATA
# =============================================================================

def create_sample_data():
    """
    Create sample/dummy data to populate the application.
    This makes the UI look filled and ready for demonstration.
    """
    # Check if data already exists
    if User.query.first():
        return
    
    print("Creating sample data...")
    
    # Sample users with diverse profiles
    sample_users = [
        {
            'email': 'alex@example.com',
            'password': 'password123',
            'name': 'Alex Johnson',
            'age': 25,
            'gender': 'Male',
            'budget': 800,
            'preferred_locations': 'Mumbai, Pune, Bangalore',
            'lifestyle': 'Non-smoker, Early riser, Gym enthusiast, Clean',
            'bio': 'Software developer looking for a quiet and clean living space. I work from home most days and enjoy cooking on weekends.'
        },
        {
            'email': 'priya@example.com',
            'password': 'password123',
            'name': 'Priya Sharma',
            'age': 23,
            'gender': 'Female',
            'budget': 600,
            'preferred_locations': 'Delhi, Noida, Gurgaon',
            'lifestyle': 'Non-smoker, Night owl, Pet-friendly, Vegetarian',
            'bio': 'Graduate student pursuing MBA. Looking for a friendly roommate who respects privacy.'
        },
        {
            'email': 'rahul@example.com',
            'password': 'password123',
            'name': 'Rahul Patel',
            'age': 28,
            'gender': 'Male',
            'budget': 1000,
            'preferred_locations': 'Bangalore, Hyderabad',
            'lifestyle': 'Social, Foodie, Movie buff, Clean',
            'bio': 'Working professional in the tech industry. Love hosting small gatherings and trying new restaurants.'
        },
        {
            'email': 'sneha@example.com',
            'password': 'password123',
            'name': 'Sneha Reddy',
            'age': 26,
            'gender': 'Female',
            'budget': 750,
            'preferred_locations': 'Hyderabad, Chennai, Bangalore',
            'lifestyle': 'Non-smoker, Yoga lover, Early riser, Minimalist',
            'bio': 'Healthcare professional working in a hospital. Looking for a peaceful environment to relax after work.'
        },
        {
            'email': 'amit@example.com',
            'password': 'password123',
            'name': 'Amit Kumar',
            'age': 24,
            'gender': 'Male',
            'budget': 500,
            'preferred_locations': 'Pune, Mumbai',
            'lifestyle': 'Student, Budget-friendly, Non-smoker, Social',
            'bio': 'Final year engineering student looking for affordable accommodation near my college.'
        },
        {
            'email': 'meera@example.com',
            'password': 'password123',
            'name': 'Meera Nair',
            'age': 27,
            'gender': 'Female',
            'budget': 900,
            'preferred_locations': 'Mumbai, Pune',
            'lifestyle': 'Working professional, Clean, Organized, Pet-friendly',
            'bio': 'Marketing professional who loves reading and gardening. Looking for a mature and responsible roommate.'
        }
    ]
    
    # Create users
    created_users = []
    for user_data in sample_users:
        user = User(
            email=user_data['email'],
            name=user_data['name'],
            age=user_data['age'],
            gender=user_data['gender'],
            budget=user_data['budget'],
            preferred_locations=user_data['preferred_locations'],
            lifestyle=user_data['lifestyle'],
            bio=user_data['bio']
        )
        user.set_password(user_data['password'])
        db.session.add(user)
        created_users.append(user)
    
    db.session.commit()
    
    # Sample listings
    sample_listings = [
        {
            'user_index': 0,
            'title': 'Cozy Private Room in Bandra',
            'location': 'Mumbai',
            'rent': 12000,
            'room_type': 'Private Room',
            'description': 'Spacious private room in a well-maintained 2BHK apartment. Close to Bandra station and local markets. Fully furnished with AC, bed, wardrobe, and study table. Common areas are shared. Flat has a modern kitchen and balcony.',
            'amenities': 'WiFi, AC, Washing Machine, Kitchen, Balcony, 24/7 Water'
        },
        {
            'user_index': 1,
            'title': 'Modern Shared Room in Sector 18',
            'location': 'Noida',
            'rent': 6000,
            'room_type': 'Shared Room',
            'description': 'Sharing basis room in a fully furnished flat. Great for students and young professionals. Near metro station and malls. Looking for a female roommate.',
            'amenities': 'WiFi, AC, Metro nearby, Gym access, Security'
        },
        {
            'user_index': 2,
            'title': 'Entire 1BHK in Koramangala',
            'location': 'Bangalore',
            'rent': 22000,
            'room_type': 'Entire Flat',
            'description': 'Beautiful 1BHK apartment in the heart of Koramangala. Walking distance to cafes, restaurants, and tech parks. Modern interiors with wooden flooring. Suitable for couples or single occupancy.',
            'amenities': 'WiFi, AC, Parking, Gym, Swimming Pool, Power Backup'
        },
        {
            'user_index': 3,
            'title': 'Peaceful Room in Gachibowli',
            'location': 'Hyderabad',
            'rent': 9000,
            'room_type': 'Private Room',
            'description': 'Quiet private room in a 3BHK apartment near IT hub. Ideal for working professionals. Fully furnished with all amenities. Vegetarian household preferred.',
            'amenities': 'WiFi, AC, Kitchen, Parking, Security, Housekeeping'
        },
        {
            'user_index': 4,
            'title': 'Budget-Friendly Shared Room',
            'location': 'Pune',
            'rent': 4500,
            'room_type': 'Shared Room',
            'description': 'Affordable shared accommodation near Hinjewadi IT Park. Best for students and freshers. Includes all basic amenities. Friendly flatmates and clean environment.',
            'amenities': 'WiFi, Common Kitchen, Water Purifier, Laundry'
        },
        {
            'user_index': 5,
            'title': 'Luxury Studio Apartment',
            'location': 'Mumbai',
            'rent': 28000,
            'room_type': 'Entire Flat',
            'description': 'Premium studio apartment in Powai with lake view. Fully furnished with high-end appliances. Gated society with all modern amenities. Perfect for professionals seeking comfort and convenience.',
            'amenities': 'WiFi, AC, Gym, Pool, Clubhouse, 24/7 Security, Covered Parking'
        },
        {
            'user_index': 0,
            'title': 'Furnished Room in Andheri',
            'location': 'Mumbai',
            'rent': 10000,
            'room_type': 'Private Room',
            'description': 'Well-ventilated room in Andheri East, close to metro and railway station. Suitable for working professionals. Flat has 3 rooms with 2 other friendly flatmates.',
            'amenities': 'WiFi, AC, Kitchen, Washing Machine'
        },
        {
            'user_index': 2,
            'title': 'Modern Flat in Whitefield',
            'location': 'Bangalore',
            'rent': 18000,
            'room_type': 'Entire Flat',
            'description': 'Contemporary 1BHK in a premium gated community in Whitefield. Close to IT parks and shopping malls. Comes with modular kitchen and spacious balcony.',
            'amenities': 'WiFi, AC, Gym, Clubhouse, Parking, Power Backup'
        }
    ]
    
    # Create listings
    for listing_data in sample_listings:
        listing = Listing(
            user_id=created_users[listing_data['user_index']].id,
            title=listing_data['title'],
            location=listing_data['location'],
            rent=listing_data['rent'],
            room_type=listing_data['room_type'],
            description=listing_data['description'],
            amenities=listing_data['amenities']
        )
        db.session.add(listing)
    
    db.session.commit()
    print("Sample data created successfully!")


# =============================================================================
# RUN APPLICATION
# =============================================================================

if __name__ == '__main__':
    # Create database tables
    with app.app_context():
        db.create_all()
        create_sample_data()
    
    # Run the Flask development server
    app.run(host='0.0.0.0', port=5000, debug=True)
