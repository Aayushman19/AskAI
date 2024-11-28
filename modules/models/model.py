from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    passwords = db.Column(db.String(100), nullable = False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    scraped_data = db.relationship('ScrapedData', backref='user', lazy=True)
    prompt_logs = db.relationship('PromptLog', backref='user', lazy=True)


class ScrapedData(db.Model):
    __tablename__ = "scraped_data"

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    content = db.Column(db.Text, nullable=True)
    meta_data = db.Column(db.JSON, nullable=True)

    created_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class PromptLog(db.Model):
    __tablename__ = "prompt_log"

    id = db.Column(db.Integer, primary_key=True)
    prompt_text = db.Column(db.Text, nullable=False)
    generated_output = db.Column(db.Text, nullable=True)

    created_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
