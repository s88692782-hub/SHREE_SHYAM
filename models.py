from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    phone = db.Column(db.String(30), default="")
    email = db.Column(db.String(120), default="")
    password_hash = db.Column(db.String(255), nullable=True)
    points = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default="Active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return (
            self.password_hash is not None
            and check_password_hash(self.password_hash, password)
        )

class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    module = db.Column(db.String(80), index=True, nullable=False)
    title = db.Column(db.String(160), nullable=False)
    details = db.Column(db.Text, default="")
    value = db.Column(db.Float, default=0)
    status = db.Column(db.String(30), default="Active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default="Published")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class WalletTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    transaction_type = db.Column(db.String(30), nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0)
    status = db.Column(db.String(30), default="Pending")
    note = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", backref="wallet_transactions")


class Market(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    # Store each weekday's active flag and opening/closing time as JSON.
    schedule_json = db.Column(db.Text, nullable=False, default="{}")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class GameRate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_name = db.Column(db.String(100), unique=True, nullable=False)
    rate = db.Column(db.Float, nullable=False, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



class UserGameHistory(db.Model):
    __tablename__ = "user_game_history"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
        index=True
    )

    game_name = db.Column(db.String(120), nullable=False)
    game_type = db.Column(db.String(80), default="Demo Game")
    session = db.Column(db.String(20), default="Open")
    selection = db.Column(db.String(255), default="")
    points_used = db.Column(db.Float, default=0)
    result = db.Column(db.String(255), default="Pending")
    status = db.Column(db.String(30), default="Pending")

    is_reverted = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    user = db.relationship(
        "User",
        backref=db.backref("game_history", lazy=True)
    )




class GameResult(db.Model):
    __tablename__ = "game_result"

    id = db.Column(db.Integer, primary_key=True)
    market_name = db.Column(db.String(120), nullable=False)
    game_type = db.Column(db.String(100), nullable=False)
    winning_number = db.Column(db.String(100), nullable=False)
    result_date = db.Column(
        db.Date,
        nullable=False,
        default=lambda: datetime.utcnow().date()
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PanaNumber(db.Model):
    __tablename__ = "pana_numbers"

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(3), unique=True, nullable=False)
    status = db.Column(db.String(20), default="Active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)