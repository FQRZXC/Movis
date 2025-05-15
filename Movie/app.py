from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///movies.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)


# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<User {self.username}>'


class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    release_year = db.Column(db.Integer, nullable=False)
    genre = db.Column(db.String(50), nullable=False)
    poster_path = db.Column(db.String(200), nullable=False)
    video_path = db.Column(db.String(200), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Movie {self.title}>'


# Helper function to get current user
@app.context_processor
def utility_processor():
    def get_user():
        if 'user_id' in session:
            return User.query.get(session['user_id'])
        return None

    return dict(get_user=get_user)


# Create database tables
with app.app_context():
    db.create_all()

    # Create admin user if not exists
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@example.com',
            password=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin)

        # Add some sample movies
        movies = [
            Movie(
                title='The Matrix',
                description='A computer hacker learns about the true nature of reality.',
                release_year=1999,
                genre='Sci-Fi',
                poster_path='matrix.jpg',
                video_path='matrix.mp4'
            ),
            Movie(
                title='Inception',
                description='A thief who steals corporate secrets through dream-sharing technology.',
                release_year=2010,
                genre='Sci-Fi',
                poster_path='inception.jpg',
                video_path='inception.mp4'
            ),
            Movie(
                title='The Shawshank Redemption',
                description='Two imprisoned men bond over a number of years.',
                release_year=1994,
                genre='Drama',
                poster_path='shawshank.jpg',
                video_path='shawshank.mp4'
            )
        ]
        db.session.add_all(movies)
        db.session.commit()


# Routes
@app.route('/')
def index():
    movies = Movie.query.order_by(Movie.date_added.desc()).all()
    return render_template('index.html', movies=movies)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Check if username or email already exists
        user_exists = User.query.filter_by(username=username).first()
        email_exists = User.query.filter_by(email=email).first()

        if user_exists:
            flash('Username already exists')
            return redirect(url_for('register'))

        if email_exists:
            flash('Email already exists')
            return redirect(url_for('register'))

        # Create new user
        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password)
        )

        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please login.')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password, password):
            flash('Please check your login details and try again.')
            return redirect(url_for('login'))

        session['user_id'] = user.id

        if user.is_admin:
            return redirect(url_for('admin_dashboard'))

        return redirect(url_for('index'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))


@app.route('/movie/<int:movie_id>')
def movie_detail(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    return render_template('movie_detail.html', movie=movie)


@app.route('/watch/<int:movie_id>')
def watch_movie(movie_id):
    if 'user_id' not in session:
        flash('Please login to watch movies')
        return redirect(url_for('login'))

    movie = Movie.query.get_or_404(movie_id)
    return render_template('watch.html', movie=movie)


# Admin routes
@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user.is_admin:
        flash('Access denied')
        return redirect(url_for('index'))

    movies = Movie.query.all()
    return render_template('admin/dashboard.html', movies=movies)


@app.route('/admin/add_movie', methods=['GET', 'POST'])
def add_movie():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user.is_admin:
        flash('Access denied')
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        release_year = request.form['release_year']
        genre = request.form['genre']

        # Handle file uploads
        poster_file = request.files['poster']
        video_file = request.files['video']

        poster_path = f"{title.lower().replace(' ', '_')}_poster.jpg"
        video_path = f"{title.lower().replace(' ', '_')}.mp4"

        # Save files
        poster_file.save(os.path.join(app.config['UPLOAD_FOLDER'], poster_path))
        video_file.save(os.path.join(app.config['UPLOAD_FOLDER'], video_path))

        new_movie = Movie(
            title=title,
            description=description,
            release_year=release_year,
            genre=genre,
            poster_path=poster_path,
            video_path=video_path
        )

        db.session.add(new_movie)
        db.session.commit()

        flash('Movie added successfully')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/add_movie.html')


@app.route('/admin/edit_movie/<int:movie_id>', methods=['GET', 'POST'])
def edit_movie(movie_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user.is_admin:
        flash('Access denied')
        return redirect(url_for('index'))

    movie = Movie.query.get_or_404(movie_id)

    if request.method == 'POST':
        movie.title = request.form['title']
        movie.description = request.form['description']
        movie.release_year = request.form['release_year']
        movie.genre = request.form['genre']

        # Handle file uploads if new files are provided
        if 'poster' in request.files and request.files['poster'].filename:
            poster_file = request.files['poster']
            movie.poster_path = f"{movie.title.lower().replace(' ', '_')}_poster.jpg"
            poster_file.save(os.path.join(app.config['UPLOAD_FOLDER'], movie.poster_path))

        if 'video' in request.files and request.files['video'].filename:
            video_file = request.files['video']
            movie.video_path = f"{movie.title.lower().replace(' ', '_')}.mp4"
            video_file.save(os.path.join(app.config['UPLOAD_FOLDER'], movie.video_path))

        db.session.commit()

        flash('Movie updated successfully')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/edit_movie.html', movie=movie)


@app.route('/admin/delete_movie/<int:movie_id>')
def delete_movie(movie_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user.is_admin:
        flash('Access denied')
        return redirect(url_for('index'))

    movie = Movie.query.get_or_404(movie_id)

    db.session.delete(movie)
    db.session.commit()

    flash('Movie deleted successfully')
    return redirect(url_for('admin_dashboard'))


if __name__ == '__main__':
    app.run(debug=True)