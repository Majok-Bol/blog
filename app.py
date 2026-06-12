from flask import Flask,render_template,url_for,redirect,request,flash
from flask_sqlalchemy import SQLAlchemy
from wtforms import StringField,BooleanField,EmailField,PasswordField,SubmitField,DateField,TextAreaField
from wtforms.validators import InputRequired,Email,EqualTo,Length
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
import email_validator
from flask_login import LoginManager,login_required,login_user,UserMixin,current_user,logout_user
from urllib.parse import urljoin,urlparse,parse_qs
#use rate limiting
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_bcrypt import Bcrypt
from datetime import datetime,UTC
import os
import uuid
from dotenv import load_dotenv
load_dotenv()
#initialize app with flask
app=Flask(__name__)
db=app.config['SQLALCHEMY_DATABASE_URI']=os.getenv("DATABASE_URL")
#initialize bcrypt
bcrypt=Bcrypt(app)
#secret key for csrf protection
app.config["SECRET_KEY"]=os.getenv("SECRET_KEY")
csrf=CSRFProtect()
#enable csrf protection globally
csrf.init_app(app)
#initialize app with the database
db=SQLAlchemy(app)
#initialize app with LoginManager class to manage user logins
login_manager=LoginManager()
login_manager.init_app(app)
login_manager.login_view="login"
#define route
@app.route("/")
def home():
    return render_template("home.html",name="Bashbytes")

#limit by username and IP
limiter=Limiter(key_func=get_remote_address,app=app,default_limits=["200 per day","50 per hour"])
def login_limit_key():
    return(request.form.get("username","")+"_"+request.remote_addr)

@app.route("/login",methods=['POST','GET'])
#only allow 5 login attempts per minute per IP
@limiter.limit("5 per minute",key_func=login_limit_key)
def login():
    #login form instance
    form=LoginForm()
    if form.validate_on_submit():
        #check if user exists in the database
        user=User.query.filter_by(username=form.username.data).first()
        # print("User found: ",user)
        if user and bcrypt.check_password_hash(user.password,form.password.data):
            flash('Login successful')
            login_user(user)
            next_page=request.args.get("next")
            if next_page and is_safe_url(next_page):
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        flash("Invalid username or password")
    return render_template("login.html",form=form)
#custom error message
@app.errorhandler(429)
def ratelimit_handler(e):
    return(render_template("429.html",message="Too many login attempts.Please try again later."),429)

#define how to secure url parsing
def is_safe_url(target):
    host_url=urlparse(request.host_url)
    # print("Host url: ",host_url)
    redirect_url=urlparse(urljoin(request.host_url,target))
    return(
        redirect_url.scheme in ("http","https") and host_url.netloc==redirect_url.netloc
    )
#handle registration feature
@app.route("/register",methods=['POST','GET'])
def register():
    #register form instance
    form=RegisterForm()
    if form.validate_on_submit():
        #check if user exists
        user=User.query.filter_by(username=form.username.data).first()
        if user:
            flash('User exists')
            return redirect(url_for('login'))
        #if not user
        #hash password
        password_hashed=bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user=User(username=form.username.data,email=form.email.data,password=password_hashed)
        #add user to the database
        db.session.add(new_user)
        #save changes to the database
        db.session.commit()
        return redirect(url_for('login'))
    return render_template("register.html",form=form)
#dashboard
@app.route('/dashboard',methods=['POST','GET'])
@login_required
def dashboard():
    return render_template('dashboard.html',username=current_user.username)
#logout user
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))
#load user
#from stored user id
'''
You will need to provide a user_loader callback
This callback is used to reload the user object from the user ID stored in the session. 
It should take the str ID of a user, and return the corresponding user object
'''
@login_manager.user_loader
def load_user(user_id):
    # return User.query.get(user_id)
    return db.session.get(User,user_id)
#using urllib
# base_url='https://fakestoreapi.com'
# target_url="/products"
# combined_url=urljoin(base_url,target_url)
# print("Combined url: ",combined_url)
# example_url=urlparse( "https://www.example.com:8080/products/laptop?id=10&sort=price#reviews")
# print("Parsed query string: ",parse_qs(example_url.query))
# print(example_url)

@app.route("/create_post",methods=["POST","GET"])
@login_required
def create_post():
    post=CreatePost()
    if post.validate_on_submit():
        new_post=Post(title=post.title.data,body=post.body.data,user_id=current_user.id)
        #add to the database
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('posts'))
    return render_template('create_post.html',post=post)
#render posts
@app.route("/posts")
def posts():
    posts=Post.query.all()
    if posts:
        return render_template("posts.html",posts=posts)
    return redirect(url_for("create_post"))

#register form class
class RegisterForm(FlaskForm):
    username=StringField("Username",validators=[InputRequired(),Length(min=4)])
    email=EmailField("Email address",validators=[InputRequired(),Email()])
    password=PasswordField("Password",validators=[InputRequired(),Length(max=255)])
    confirm_password=PasswordField("Confirm password",validators=[InputRequired(),])
    submit=SubmitField("Sign up")

#login form class
class LoginForm(FlaskForm):
    username=StringField("Username",validators=[InputRequired(),Length(min=4)])
    password=PasswordField(validators=[InputRequired(),Length(max=255)])
    submit=SubmitField("Login")
#text area for creating post
class CreatePost(FlaskForm):
    created_at=DateField("Created_at",format='%Y-%m-%d',default=lambda:datetime.now(UTC))
    title=StringField("Title",validators=[InputRequired(),Length(min=4)])
    body=TextAreaField("Body",validators=[InputRequired(),Length(min=10)])
    submit=SubmitField("Create post")
#create database 
#use uuid4 instead of incrementing IDs
class User(db.Model,UserMixin):
    __tablename__="users"
    id=db.Column(db.String(255),primary_key=True,default=lambda:str(uuid.uuid4()))
    username=db.Column(db.String(50),nullable=False,unique=True)
    email=db.Column(db.String(100),nullable=False,unique=True)
    password=db.Column(db.String(255),nullable=False,unique=True)
    posts=db.relationship("Post",back_populates="author")
#create post table
class Post(db.Model):
    __tablename__="posts"
    post_id=db.Column(db.String(255),primary_key=True,default=lambda:str(uuid.uuid4()))
    title=db.Column(db.String(100))
    body=db.Column(db.Text)
    #user id is a foreign key which is a primary key in users table
    user_id=db.Column(db.String,db.ForeignKey("users.id"))
    author=db.relationship("User",back_populates="posts")
#check if app is run from current module
if __name__=="__main__":
    with app.app_context():
        #create data in the database
        db.create_all()
        #delete database data
        #  db.drop_all()
    app.run(debug=True)