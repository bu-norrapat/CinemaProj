from flask import Flask, render_template, redirect, url_for, request, session, flash
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

class Movies(db.Model):
    _id = db.Column("movie_id", db.Integer, primary_key=True)
    movie_name = db.Column(db.String(360), unique=True, nullable=False)
    movie_duration = db.Column(db.Integer, nullable=False)

    def __init__(self, movie_name, movie_duration):
        self.movie_name = movie_name
        self.movie_duration = movie_duration

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

class Tickets(FlaskForm):
    Seat_row = StringField('')

    pass

def index():
    return redirect(url_for('home'))

def home():
    movies = Movies.query.all()

    # Get current date information
    current_year = datetime.now().year
    current_month = datetime.now().month
    current_day = datetime.now().day
    

    if 'user_email' in session:
        user_email = session['user_email']

        return render_template(
            'home.html', 
            user_email=user_email, 
            movies=movies, 
            logged_in=True,
            current_year=current_year, 
            current_month=current_month, 
            current_day=current_day
        )
    else:

        return render_template(
            'home.html', 
            movies=movies, 
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
    # Example: Simulating movie data retrieval
    movie = Movies.query.get_or_404(movie_id)
    return render_template('movie_detail.html', movie=movie)

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