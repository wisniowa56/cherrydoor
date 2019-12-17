#flask-connected imports:
from flask import Flask
from flask_pymongo import PyMongo
from flask_login import current_user, LoginManager, UserMixin
from flask_restful import Resource, Api, reqparse, inputs, abort
from flask_socketio import SocketIO, emit, disconnect
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired
#hashing function import:
from argon2 import PasswordHasher
#built-in libraries import:
from json import load
import datetime as dt

with open('config.json', 'r', encoding='utf-8') as f: #load configuration file
    config = load(f) #convert confuguration to a dictionary using json.load()

class LoginForm(FlaskForm): #create fields for login form with labels based on translations form config.json file
    username = StringField(config['login-translation']['username'], validators=[DataRequired()], render_kw={"placeholder": config['login-translation']['username']}) 
    password = PasswordField(config['login-translation']['password'], validators=[DataRequired()], render_kw={"placeholder": config['login-translation']['password']})
    remember = BooleanField(config['login-translation']['remember-me'])
    submit = SubmitField(config['login-translation']['log-in'])

#app creation
app = Flask(__name__, template_folder='../templates', static_folder="../static") #create a Flask instance
app.config["SECRET_KEY"] = config['secret-key'] #set up a secret key for cookie and session encryption based on config.json

#pymongo connection
app.config["MONGO_URI"] = f"mongodb://{config['mongo']['url']}/{config['mongo']['name']}" #configure mongodb access uri
try:
    mongo = PyMongo(app, username=config['mongo']['username'], password=config['mongo']['password']).db #set up PyMongo using credentials from config.json
except KeyError:
    mongo = PyMongo(app).db
login_manager = LoginManager() #create login_manager for flask_login
login_manager.login_view = 'login' #default view (page) used for logging in
login_manager.session_protection = "strong" #set a better session protection
login_manager.login_message = config['login-translation']['message'] #message shown to anonymous users when a page requires being logged in - set in config.json
login_manager.init_app(app) #initialize the login_manager

hasher = PasswordHasher() #create an argon2 hasher instance that will be called for all future operations

api = Api(app) #create a restful api instance from flask_restful

parser = reqparse.RequestParser()

socket = SocketIO(app)

class User(UserMixin):
    '''
    User class used by flask_login
    '''
    def __init__(self, username):
        self.username = username
    
    @staticmethod
    def is_authenticated(self):
        '''
        Authentication status
        '''
        return True
    
    @staticmethod
    def is_active(self):
        '''
        Shows that the user is logged in
        '''
        return True
    
    @staticmethod
    def is_anonymous(self):
        '''
        A logged in user is not anonymous
        '''
        return False
    def get_id(self):
        '''
        Returns the id - in this case username
        '''
        return self.username
    def get_cards(self):
        '''
        Returns all mifare card ids associated with the account
        '''
        return mongo.users.find_one({"name":self.username})['cards']
    def add_card(self, card):
        '''
        adds a mifare card id to user profile
        '''
        mongo.users.update_one({"name":self.username}, { "$push": {"cards":card}}, upsert=True)
    def delete_card(self, card):
        '''
        adds a mifare card id from user profile
        '''
        mongo.users.update_one({"name":self.username}, { "$pull": {"cards":card}})        

@login_manager.user_loader 
def load_user(username):
    '''
    A function for loading users from database by username
    '''
    u = mongo.users.find_one({"name": username})
    if not u:
        return None
    return User(username=u['name'])


import cherrydoor.api
import cherrydoor.routes
import cherrydoor.websockets