from flask import Flask,render_template
from flask_sqlalchemy import SQLAlchemy
from wtforms import StringField,BooleanField,EmailField,PasswordField,SubmitField
from wtforms.validators import InputRequired,Email,EqualTo,Length
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
import os
from dotenv import load_dotenv
load_dotenv()
#initialize app with flask
app=Flask(__name__)
db=app.config['SQLALCHEMY_DATABASE_URI']=os.getenv("DATABASE_URL")
#secret key for csrf protection
app.config["SECRET_KEY"]=os.getenv("SECRET_KEY")
csrf=CSRFProtect()
#enable csrf protection globally
csrf.init_app(app)
#initialize app with the database
db=SQLAlchemy(app)
#define route
@app.route("/")
def home():
    return render_template("home.html",name="Bashbytes")

@app.route("/login")
def login():
    return render_template("login.html")
@app.route("/register")
def register():
    form=RegisterForm()
    return render_template("register.html",form=form)


#form instance
class RegisterForm(FlaskForm):
    username=StringField("Username",validators=[InputRequired(),Length(min=4)])
    email=EmailField("Email address",validators=[InputRequired(),Email()])
    password=PasswordField("Password",validators=[InputRequired(),Length(max=255)])
    confirm_password=PasswordField("Confirm password",validators=[InputRequired(),])
    submit=SubmitField("Sign up")
#check if app is run from current module
if __name__=="__main__":
    app.run(debug=True)