from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_migrate import Migrate
from flaskApp.models import db, User, Transaction
from sqlalchemy import func
from pathlib import Path
import os

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "finance-tracker-dev-secret")

# Prefer SQLite locally for simplicity; Render can still use a PostgreSQL DATABASE_URL if supplied.
db_url = os.environ.get("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url or f"sqlite:///{BASE_DIR / 'finance.db'}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
migrate = Migrate(app, db)

with app.app_context():
    db.create_all()


@app.route('/')
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    uid = int(session["user_id"])
    recent_5 = (
        Transaction.query
        .filter_by(uid=uid)
        .order_by(Transaction.tid.desc())
        .limit(5)
        .all()
    )

    income = db.session.query(func.sum(Transaction.amount)).filter_by(uid=uid, type="credit").scalar() or 0
    expense = db.session.query(func.sum(Transaction.amount)).filter_by(uid=uid, type="debit").scalar() or 0
    balance = income - expense

    return render_template(
        "home.html",
        msg=str(session["username"]).capitalize(),
        recent_5=recent_5,
        income=float(income),
        balance=float(balance),
        expense=float(expense)
    )


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        confirm_password = request.form.get('confirm_password')

        if not username or not password:
            flash("Please complete all fields.")
            return redirect(url_for('register'))

        if confirm_password and password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash("Username already registered.")
            return redirect(url_for('register'))

        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please login.")
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.uid
            session['username'] = user.username
            return redirect(url_for('home'))
        flash("Invalid username or password")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/addtrac', methods=['GET', 'POST'])
def addtrac():
    if "user_id" not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        amount = float(request.form['amount'])
        t_type = request.form['type']
        desc = request.form['description'].strip() or 'General transaction'

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
    if "user_id" not in session:
        return redirect(url_for('login'))

    transactions = Transaction.query.filter_by(uid=int(session['user_id'])).order_by(Transaction.tid.desc()).all()
    return render_template('transactions.html', transactions=transactions)


@app.route('/transactions/delete/<int:id>', methods=['POST'])
def delete_trac(id):
    if "user_id" not in session:
        return redirect(url_for('login'))

    transaction = Transaction.query.filter_by(tid=id, uid=int(session['user_id'])).first_or_404()
    db.session.delete(transaction)
    db.session.commit()
    return redirect(url_for('transactions'))


if __name__ == "__main__":
    app.run(debug=False)
