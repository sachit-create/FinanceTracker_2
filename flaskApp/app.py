from flask import Flask , render_template , request , redirect , url_for , session , flash
from flask_migrate import Migrate
from models import db , User , Transaction
from flask_login import login_required , current_user

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db'
app.config['SECRET_KEY'] = 'VERY_SECRET_KEY'
db.init_app(app)
migrate = Migrate(app,db)

@app.route('/')
def home():
    if "user_id" not in session : 
        return redirect(url_for("login"))
    return render_template("home.html", msg=str(session['username']).capitalize())

@app.route('/register' , methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash("username already registered")
            return redirect(url_for("register"))
        
    
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration sucessful! Please login.")
        return redirect(url_for("login"))
    
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.uid
            session['username'] = user.username
            return redirect(url_for("home"))
        else:
            flash("Invalid username or password")
        
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route('/addtrac', methods=['GET', 'POST'])
@login_required
def add_trac():
    if request.method == 'POST':
        amount = request.form['amount']
        t_type = request.form['type']
        desc = request.form['description']

        txn = Transaction(
            uid=current_user.uid,  
            amount=amount,
            type=t_type,
            description=desc
        )
        db.session.add(txn)
        db.session.commit()

        return redirect(url_for('home')) 

    return render_template('tracform.html')

if __name__=='__main__':
    app.run(host='0.0.0.0',debug=True)