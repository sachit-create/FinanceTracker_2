from flask import Flask , render_template , request , redirect , url_for , session , flash
from flask_migrate import Migrate
from flaskApp.models import db , User , Transaction
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func 
import os

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

db_url = os.environ.get("DATABASE_URL")

if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db'
# app.config['SECRET_KEY'] = 'VERY_SECRET_KEY'
db.init_app(app)
migrate = Migrate(app,db)

@app.route('/')
def home():
    if "user_id" not in session : 
        return redirect(url_for("login"))
    recent_5 = (
        Transaction.query
        .filter_by(uid=int(session['user_id']))
        .order_by(Transaction.tid.desc())  
        .limit(5)
        .all()
    )

    uid = int(session['user_id'])
    transactions = Transaction.query.filter_by(uid=uid).all()

    income = db.session.query(func.sum(Transaction.amount)).filter_by(uid=uid, type="credit").scalar() or 0

    expense = db.session.query(func.sum(Transaction.amount)).filter_by(uid=uid, type="debit").scalar() or 0

    balance = income - expense

    return render_template("home.html", msg=str(session['username']).capitalize(),recent_5=recent_5,
    income=income,balance=balance,expense=expense)

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
def addtrac():
    if request.method == 'POST':
        amount = request.form['amount']
        t_type = request.form['type']
        desc = request.form['description']

        txn = Transaction(
            uid=int(session['user_id']),  
            amount=amount,
            type=t_type,
            description=desc
        )
        db.session.add(txn)
        db.session.commit()

        return redirect(url_for('transactions')) 
    return render_template('tracform.html')

@app.route('/transactions')
def transactions():
    transactions = Transaction.query.filter_by(uid=int(session['user_id'])).all()
    return render_template('transactions.html', transactions=transactions)

@app.route('/transactions/delete/<int:id>', methods=['POST'])
def delete_trac(id):
    transaction = Transaction.query.get_or_404(id)
    db.session.delete(transaction)
    db.session.commit()
    return redirect(url_for('transactions'))

if __name__ == "__main__":
    app.run(debug=False)

