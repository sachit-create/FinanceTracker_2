from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
        __tablename__ = 'users'

        uid = db.Column(db.Integer,primary_key=True)
        username = db.Column(db.String,nullable=False, unique=True)
        password_hash = db.Column(db.String,nullable=False)

        def set_password(self, password):
                self.password_hash = generate_password_hash(password)

        def check_password(self , password):
                return check_password_hash(self.password_hash,password)
        
class Transaction(db.Model):
        pass


