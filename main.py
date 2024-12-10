from flask import Flask, jsonify, render_template, redirect, url_for, request, session, flash
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, EmailField, IntegerField
from wtforms.validators import InputRequired, Length, ValidationError, DataRequired, NumberRange
from flask_bcrypt import Bcrypt

class FlaskAppWrapper(object):
    def __init__(self, app, **configs):
        self.app = app
        self.configs(**configs)
    def configs(self, **configs):
        for config, value in configs.items():
            self.app.config[config.upper()] = value
    def add_endpoint(self, endpoint=None, endpoint_name=None, handler=None, methods=['GET'], *args, **kwargs):
        self.app.add_url_rule(endpoint, endpoint_name, handler, methods=methods, *args, **kwargs)
    def run(self, **kwargs):
        self.app.run(**kwargs)

flask_app = Flask(__name__)

app = FlaskAppWrapper(flask_app, SQLALCHEMY_DATABASE_URI='sqlite:///database.db', SECRET_KEY='GoldenEagle')
bcrypt = Bcrypt(flask_app)
db = SQLAlchemy(flask_app)

class Users(db.Model):
    _id = db.Column("user_id", db.Integer, primary_key=True)
    user_email = db.Column(db.String(360), unique=True, nullable=False)
    user_password = db.Column(db.String(255), nullable=False)
    user_is_admin = db.Column( db.Boolean, nullable=False, default=False)

    def __init__(self, user_email, user_password, user_is_admin):
        self.user_email = user_email
        self.user_password = user_password
        self.user_is_admin = user_is_admin

class Theaters(db.Model):
    _id = db.Column("theater_id", db.Integer, primary_key=True)
    

class RegisterForm(FlaskForm):
    user_email = EmailField(validators=[InputRequired()], render_kw={"placeholder":"Email"})
    user_password = PasswordField(validators=[InputRequired(), Length(min=8, max=64)], render_kw={"placeholder":"Password"})
    conf_password = PasswordField(validators=[InputRequired(), Length(min=8, max=64)], render_kw={"placeholder":"Confirm Password"})

    submit = SubmitField("Register")

    def validate_email(self, user_email):
        existing_user_email = Users.query.filter_by(user_email=user_email.data).first()
        if existing_user_email:
            raise ValidationError("Email already registered.")

class LoginForm(FlaskForm):
    user_email = EmailField(validators=[InputRequired()], render_kw={"placeholder":"Email"})
    user_password = PasswordField(validators=[InputRequired(), Length(min=8, max=64)], render_kw={"placeholder":"Password"})

    submit = SubmitField("Login")

class MovieForm(FlaskForm):
    movie_name = StringField('Movie Name', validators=[DataRequired(), Length(min=1, max=360)])
    movie_duration = IntegerField('Duration (mins)', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Add Movie')

class Ticket(db.Model):
    __tablename__ = 'Tickets'
    
    # Define the columns for the Ticket table
    id = db.Column("Id",db.Integer, primary_key=True)
    seat_row = db.Column("Seat_Row",db.Text, nullable=False)  # Store single character like 'A', 'B', etc.
    seat_column = db.Column("Seat_Column",db.Integer, nullable=False)
    movie_id = db.Column("Movie_id",db.Integer, db.ForeignKey('movies.movie_id'), nullable=False)  
    showtime_id = db.Column("Showtime_id",db.Integer, db.ForeignKey('Showtimes.id'), nullable=False)
    user_id = db.Column("User_id",db.Integer, db.ForeignKey('users.user_id'), nullable=False)

    # Relationships to other models
    movie = db.relationship('Movies', backref='tickets', lazy=True)
    showtime = db.relationship('Showtime', back_populates='tickets')  # Keep back_populates
    user = db.relationship('Users', backref='tickets', lazy=True)

    def __init__(self, seat_row, seat_column, movie_id, showtime_id, user_id):
        self.seat_row = seat_row
        self.seat_column = seat_column
        self.movie_id = movie_id
        self.showtime_id = showtime_id
        self.user_id = user_id

class Movies(db.Model):
    __tablename__ = 'movies'
    _id = db.Column("movie_id", db.Integer, primary_key=True)
    movie_name = db.Column(db.String(360), unique=True, nullable=False)
    movie_duration = db.Column(db.Integer, nullable=False)

    # Set the backref name to 'schedules'
    schedules = db.relationship('Schedule', backref='movie_schedules', lazy=True)

    def __init__(self, movie_name, movie_duration):
        self.movie_name = movie_name
        self.movie_duration = movie_duration


class Schedule(db.Model):
    __tablename__ = 'Schedules'
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.movie_id'))
    start_time = db.Column(db.Text)
    end_time = db.Column(db.Text)
    repeat_days = db.Column(db.Integer)

    movie = db.relationship('Movies', backref='movie_schedule', lazy=True)
    
    # Link to Showtimes through back_populates
    showtimes = db.relationship('Showtime', back_populates='schedule', lazy=True)

    def __init__(self, show_year, show_month, show_date, movie_id):
        self.show_year = show_year
        self.show_month = show_month
        self.show_date = show_date
        self.movie_id = movie_id

class Showtime(db.Model):
    __tablename__ = 'Showtimes'
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('Schedules.id'))
    show_year = db.Column(db.Integer)
    show_month = db.Column(db.Integer)
    show_date = db.Column(db.Integer)

    # Link to Movie and Schedule using back_populates
    schedule = db.relationship('Schedule', back_populates='showtimes')
    tickets = db.relationship('Ticket', back_populates='showtime', lazy=True)  # Use back_populates instead of backref

    def __init__(self, show_year, show_month, show_date, schedule_id):
        self.show_year = show_year
        self.show_month = show_month
        self.show_date = show_date
        self.schedule_id = schedule_id

def index():
    return redirect(url_for('home'))

def save_seat():
    data = request.get_json()  # Parse JSON data from the request
    row = data.get('row')
    column = data.get('column')
    movie_id = data.get('movie_id')
    showtime_id = data.get('showtime_id')

    # Perform seat booking logic (e.g., checking if the seat is available)
    existing_ticket = Ticket.query.filter_by(
        seat_row=row,
        seat_column=column,
        movie_id=movie_id,
        showtime_id=showtime_id
    ).first()

    if existing_ticket:
        return jsonify({
            "status": "error",
            "message": f"Seat {row}{column} is already booked."
        })

    # Create new ticket if seat is available
    new_ticket = Ticket(
        seat_row=row,
        seat_column=column,
        movie_id=movie_id,
        showtime_id=showtime_id,
        user_id=session.get('user_email')  # Assuming user is logged in
    )
    db.session.add(new_ticket)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": f"Seat {row}{column} booked successfully!",
        "movie_id": movie_id,
        "showtime_id": showtime_id,
        "seat": f"{row}{column}"
    })


def home():
    # Adjust the query to join Schedule and Showtime models properly
    movies = db.session.query(Movies, Schedule, Showtime).join(Schedule, Schedule.movie_id == Movies._id) \
        .join(Showtime, Showtime.schedule_id == Schedule.id).all()

    # Get current date information
    current_year = datetime.now().year
    current_month = datetime.now().month
    current_day = datetime.now().day
    
    movie_data = []
    for movie, schedule, showtime in movies:
        movie_data.append({
            'movie_name': movie.movie_name,
            'movie_duration': movie.movie_duration,
            'start_time': schedule.start_time,  # Access start_time from Schedule
            'end_time': schedule.end_time       # Access end_time from Schedule
        })

    if 'user_email' in session:
        user_email = session['user_email']
        return render_template(
            'home.html', 
            user_email=user_email, 
            movie_data=movie_data,  # Pass movie data with all details
            logged_in=True,
            current_year=current_year, 
            current_month=current_month, 
            current_day=current_day
        )
    else:
        return render_template(
            'home.html', 
            movie_data=movie_data,  # Pass movie data for not logged-in user
            logged_in=False,
            current_year=current_year, 
            current_month=current_month, 
            current_day=current_day
        )
    
def admin():
    form = MovieForm()
    if form.validate_on_submit():
        # Add movie to the database
        new_movie = Movies(movie_name=form.movie_name.data, movie_duration=form.movie_duration.data)
        try:
            db.session.add(new_movie)
            db.session.commit()
            flash("Movie added successfully!", "success")
        except:
            db.session.rollback()
            flash("Movie already exists or an error occurred.", "danger")
        return redirect(url_for("admin"))

    # Fetch all movies to display
    movies = Movies.query.all()
    return render_template("admin.html", form=form, movies=movies)

def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = request.form.get('user_email')
        password = request.form.get('user_password')
        user = Users.query.filter_by(user_email=email).first()
        if user and bcrypt.check_password_hash(user.user_password, password):

            session['user_email'] = user.user_email
            flash("Login successful", "success")
            print(session.get('user_email'))
            return redirect(url_for('home'))
        else:
            flash("Invalid email or password", "error")
            return redirect(url_for('login'))
    else:
        return render_template('login.html', form = form)

def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.user_password.data)
        new_user = Users(user_email=form.user_email.data, user_password=hashed_password, user_is_admin=False)
        db.session.add(new_user)
        db.session.commit()
        flash("Register complete")
        return redirect(url_for('login'))
    else:
        return render_template('register.html', form = form)

def logout():
    session.clear()
    flash("You have been logged out", "info")
    return redirect(url_for('home'))

def movie_detail(movie_id):
    # Retrieve movie by ID, or return a 404 if not found
    showtimes = db.session.query(Showtime, Schedule).join(Schedule, Schedule.id == Showtime.schedule_id) \
        .filter(Showtime.schedule.has(movie_id=movie_id)).all()
    
    movie = Movies.query.get_or_404(movie_id)
    
    # Get the user email from the session
    user_email = session.get('user_email')
    
    # If the user is logged in, pass the user_email
    if user_email:
        user_id = user_email  # Or any other identifier like user_id if needed
    else:
        user_id = None  # If user is not logged in, set to None
    
    # If no showtimes are found, handle it
    if not showtimes:
        return "No showtimes available for this movie", 404

    # Prepare movie data and showtimes for rendering
    showtime_data = []
    for showtime, schedule in showtimes:
        showtime_data.append({
            'showtime_id': showtime.id,
            'movie_name': movie.movie_name,
            'start_time': schedule.start_time,
            'end_time': schedule.end_time,
            'show_year': showtime.show_year,
            'show_month': showtime.show_month,
            'show_day': showtime.show_date,
        })
    print(f"User ID passed to template: {user_id}")

    # Pass both movie and showtimes to the template
    return render_template('movie_detail.html',user_id=session.get('user_email'),movie_id=movie_id, movie=movie, showtimes=showtime_data, showtime=showtime)

def get_movies():
    selected_date = request.args.get('date')  # Get the selected date (YYYY-MM-DD format)
    selected_year, selected_month, selected_day = selected_date.split('-')
    
    # Convert the string date components to integers
    results = db.session.query(Movies, Schedule, Showtime).join(Schedule, Schedule.movie_id == Movies._id) \
        .join(Showtime, Showtime.schedule_id == Schedule.id) \
        .filter(Showtime.show_year == int(selected_year), 
                Showtime.show_month == int(selected_month), 
                Showtime.show_date == int(selected_day)) \
        .all()

    # Prepare the response with movie data
    movie_data = []
    for movie, schedule, showtime in results:
        movie_data.append({
            'movie_id' : movie._id,
            'movie_name': movie.movie_name,
            'movie_duration': movie.movie_duration,
            'start_time': schedule.start_time,  # Access start_time from Schedule
            'end_time': schedule.end_time       # Access end_time from Schedule
        })

    return jsonify({'movies': movie_data})



def tickets():
    # Retrieve query parameters from the URL
    user_email = session.get('user_email')

    if not user_email:
        return "User not logged in", 401  # Return an error if the user is not logged in

    # Query the ticket information from the database using the user_email
    ticket_info = db.session.query(Ticket, Showtime, Schedule, Movies) \
        .join(Showtime, Showtime.id == Ticket.showtime_id) \
        .join(Schedule, Schedule.id == Showtime.schedule_id) \
        .join(Movies, Movies._id == Ticket.movie_id) \
        .filter(Ticket.user_id == user_email)  # Assuming Ticket model has user_email field

    # If no ticket is found for the user, return an error
    if not ticket_info:
        return "Ticket not found", 404

    # Assuming there is only one ticket for simplicity (or you could handle multiple tickets if needed)
    ticket_data = {
        'movie_name': ticket_info.Movies.movie_name,
        'seat': ticket_info.seat,
        'showtime': ticket_info.Showtime.show_time,  # Adjust to match your actual field names
        'end_time': ticket_info.Showtime.end_time,  # Adjust to match your actual field names
    }

    # Render the tickets page with ticket data
    return render_template('tickets.html', ticket_info=ticket_data)

app.add_endpoint('/tickets', 'tickets', tickets, methods=['GET'])
app.add_endpoint('/save-seat', 'save-seat', save_seat, methods=['POST'])
app.add_endpoint('/get_movies', 'get_movies', get_movies, methods=['GET'])
app.add_endpoint('/', 'index', index, methods=['GET'])
app.add_endpoint('/home', 'home', home, methods=['GET'])
app.add_endpoint('/register', 'register', register, methods=['GET','POST'])
app.add_endpoint('/login', 'login', login, methods=['GET','POST'])
app.add_endpoint('/logout', 'logout', logout, methods=['GET'])
app.add_endpoint('/admin', 'admin', admin, methods=['GET','POST'])
app.add_endpoint('/movie/<int:movie_id>', 'movie_detail', movie_detail, methods=['GET'])


if __name__ == "__main__":
    with flask_app.app_context():
        db.create_all()
    app.run(debug=True)