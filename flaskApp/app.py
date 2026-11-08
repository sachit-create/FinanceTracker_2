from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_migrate import Migrate
from flaskApp.models import db, User, Transaction
from sqlalchemy import func
from pathlib import Path
from datetime import date, timedelta
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


def build_financial_summary(transactions, today=None):
    """Create private, data-grounded insights using a small local rules engine."""
    today = today or date.today()
    month_start = today.replace(day=1)
    last_30_days = today - timedelta(days=29)
    previous_period_start = last_30_days - timedelta(days=30)

    totals = {"credit": 0.0, "debit": 0.0}
    month_totals = {"credit": 0.0, "debit": 0.0}
    recent_totals = {"credit": 0.0, "debit": 0.0}
    previous_totals = {"credit": 0.0, "debit": 0.0}
    month_expenses_by_category = {}
    insights = []

    category_keywords = {
        "Food & dining": ("food", "restaurant", "cafe", "coffee", "lunch", "dinner", "grocery", "groceries", "swiggy", "zomato"),
        "Transport": ("uber", "ola", "fuel", "petrol", "transport", "bus", "train", "metro", "flight", "cab"),
        "Shopping": ("shop", "shopping", "amazon", "flipkart", "clothes", "store", "purchase"),
        "Bills & utilities": ("bill", "electric", "water", "internet", "recharge", "rent", "utility", "phone"),
        "Health": ("health", "medical", "doctor", "pharmacy", "medicine", "hospital"),
        "Entertainment": ("movie", "music", "game", "netflix", "spotify", "entertainment", "concert"),
    }

    def transaction_date(transaction):
        value = transaction.created_at
        return value.date() if hasattr(value, "date") else today

    for transaction in transactions:
        amount = float(transaction.amount or 0)
        kind = transaction.type
        txn_date = transaction_date(transaction)
        totals[kind] += amount
        if txn_date >= month_start:
            month_totals[kind] += amount
            if kind == "debit":
                description = (transaction.description or "").lower()
                category = next((name for name, words in category_keywords.items() if any(word in description for word in words)), "Other")
                month_expenses_by_category[category] = month_expenses_by_category.get(category, 0) + amount
        if last_30_days <= txn_date <= today:
            recent_totals[kind] += amount
        elif previous_period_start <= txn_date < last_30_days:
            previous_totals[kind] += amount

    current_net = month_totals["credit"] - month_totals["debit"]
    overall_balance = totals["credit"] - totals["debit"]
    recent_expenses = recent_totals["debit"]
    previous_expenses = previous_totals["debit"]
    top_categories = sorted(month_expenses_by_category.items(), key=lambda item: item[1], reverse=True)[:5]

    if not transactions:
        insights.append("Add a transaction to start building a personalized view of your finances.")
    else:
        if recent_expenses == 0:
            insights.append("No expenses have been recorded in the last 30 days. Add recent activity for a more current picture.")
        elif previous_expenses > 0:
            change = (recent_expenses - previous_expenses) / previous_expenses * 100
            if change >= 10:
                insights.append(f"Your recorded expenses are up {change:.0f}% compared with the previous 30 days.")
            elif change <= -10:
                insights.append(f"Your recorded expenses are down {abs(change):.0f}% compared with the previous 30 days.")
            else:
                insights.append("Your recorded spending has stayed fairly steady compared with the previous 30 days.")
        else:
            insights.append("Your recent expenses are the first recorded in the last 60 days, so there is no earlier period to compare.")

        if month_totals["credit"] > 0:
            saved_percent = current_net / month_totals["credit"] * 100
            if current_net >= 0:
                insights.append(f"You have kept {saved_percent:.0f}% of this month’s recorded income after expenses.")
            else:
                insights.append("This month’s recorded expenses are higher than its recorded income.")
        elif month_totals["debit"] > 0:
            insights.append("There is spending recorded this month but no income yet; add any missing income for a more complete summary.")

        if top_categories:
            category, amount = top_categories[0]
            insights.append(f"{category} is your largest categorized expense this month at ₹{amount:,.2f}.")

    return {
        "total_income": totals["credit"],
        "total_expense": totals["debit"],
        "overall_balance": overall_balance,
        "month_income": month_totals["credit"],
        "month_expense": month_totals["debit"],
        "month_net": current_net,
        "recent_income": recent_totals["credit"],
        "recent_expense": recent_expenses,
        "transaction_count": len(transactions),
        "month_transaction_count": sum(1 for txn in transactions if transaction_date(txn) >= month_start),
        "top_categories": top_categories,
        "insights": insights,
        "month_label": today.strftime("%B %Y"),
    }


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


@app.route('/summary')
def summary():
    if "user_id" not in session:
        return redirect(url_for('login'))

    transactions = (
        Transaction.query
        .filter_by(uid=int(session['user_id']))
        .order_by(Transaction.created_at.desc(), Transaction.tid.desc())
        .all()
    )
    financial_summary = build_financial_summary(transactions)
    return render_template(
        'summary.html',
        msg=str(session['username']).capitalize(),
        summary=financial_summary,
        recent_transactions=transactions[:5],
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
