from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime, timezone

db = SQLAlchemy()

class User(db.Model, UserMixin):
        __tablename__ = 'users'

        uid = db.Column(db.Integer,primary_key=True)
        username = db.Column(db.String(255),nullable=False, unique=True)
        password_hash = db.Column(db.String(200),nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

        # relationship with Transaction
        transactions = db.relationship('Transaction', backref='user', lazy=True, cascade="all, delete")


        def set_password(self, password):
                self.password_hash = generate_password_hash(password)

        def check_password(self , password):
                return check_password_hash(self.password_hash,password)
        
class Transaction(db.Model):
        __tablename__ = 'transactions'
    
        tid = db.Column(db.Integer, primary_key=True, autoincrement=True)
        uid = db.Column(db.Integer, db.ForeignKey('users.uid'), nullable=False)
        amount = db.Column(db.Numeric(10,2), nullable=False)
        type = db.Column(db.Enum('credit', 'debit', name='transaction_type'), nullable=False)
        description = db.Column(db.Text)
        created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

        
