from cherrydoor import app, mongo, hasher, LoginForm, login_manager, User
from flask import render_template, url_for, request, session, redirect, flash
from flask_login import current_user, login_user, logout_user, login_required
from argon2.exceptions import VerificationError #import VerificationError thrown when password doesn't match the hash


@app.route('/') #dashboard page
@login_required
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST']) #login page
def login():
    form = LoginForm() #load the form
    if form.validate_on_submit():
        login_username = mongo.users.find_one({'name' : str(form.username.data)})
        if login_username:
            try:
                if login_username['password']!='' and hasher.verify(login_username['password'].encode('utf-8'), form.password.data.encode('utf-8')):
                    user_obj = User(username=form.username.data)
                    login_user(user_obj, remember = form.remember.data)
                    return redirect(url_for('index')) #if login was succesful - redirect user to the dashboard
                else:
                    return render_template('login.html', form=form, username_error="  is-invalid", password_error=" is-invalid")
            except VerificationError: #if argon2 throws VerificationError it means the password doesn't match the hash for this username
                return render_template('login.html', form=form, username_error="", password_error=" is-invalid")
            except KeyError:
                return render_template('login.html', form=form, username_error="  is-invalid", password_error=" is-invalid")
        return render_template('login.html', form=form, username_error=" is-invalid ", password_error="") #if there is no user with this username, return Invalid username. 
    return render_template('login.html', form=form, username_error="", password_error="")

@app.route('/register', methods=['POST', 'GET'])
@login_required
def register():
    if request.method == 'POST':
        users = mongo.users
        existing_user = users.find_one({'name' : request.form['username']})

        if existing_user is None:
            hashpass = hasher.hash(request.form['pass'].encode('utf-8'))
            users.insert({'name' : request.form['username'], 'password' : hashpass, 'cards':[request.form['card']]})
            session['username'] = request.form['username']
            return redirect(url_for('index'))
        
        return 'That username already exists!'

    return render_template('register.html')


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for('login'))