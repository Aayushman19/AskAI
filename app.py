from flask import Flask, render_template, flash, redirect, url_for, session, logging, request, jsonify
from flask_bcrypt import Bcrypt
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os, logging
import secrets
from modules.models.model import db, User, ScrapedData, PromptLog
import requests
from bs4 import BeautifulSoup
import json, pytz
from flask_mail import Mail, Message

load_dotenv()

app = Flask(__name__, template_folder="modules/templates", static_folder="modules/static")

rapidapi_key = os.getenv("RAPIDAPI_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')


db.init_app(app)

bcrypt = Bcrypt(app)

file_handler = logging.FileHandler(filename='app.log', mode='w')
stream_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s [%(levelname)s]: %(message)s')

file_handler.setFormatter(formatter)

logging.basicConfig(
    level=logging.INFO,
    handlers= [file_handler, stream_handler]
)

logger = logging.getLogger(__name__)

try:
    with app.app_context():
        db.create_all()
        print("Registered Tables:", db.metadata.tables.keys())

except Exception as e:
    print(f"Error during table creation: {e}")


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods = ["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email = email).first()

        if user and bcrypt.check_password_hash(user.passwords, password):
            session["user_id"] = user.id
            session["user_name"] = user.name
            flash("Login Successful, Success!")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid User or Password, Login Failed")
            return redirect(url_for('login'))
        
    return render_template('login.html')

@app.route('/dashboard', methods = ["GET","POST"])
def dashboard():
    if 'user_id' not in session:
        flash("Please log in the dashboard.", "warning")
        return redirect(url_for('login'))
    
    user_name = session.get("user_name", "User")
    return render_template("dashboard.html", user_name = user_name)

@app.route('/profile', methods=["GET", "POST"])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)

    currTime = datetime.now(timezone.utc)

    if user.created_at.tzinfo is None:
        created_at_aware = user.created_at.replace(tzinfo=timezone.utc)
    else:
        created_at_aware = user.created_at
    
    doj = (currTime - created_at_aware).days
    uses_ai = len(user.prompt_logs)
    uses_web = len(user.scraped_data)

    return render_template("profile.html", 
            name = user.name, 
            days_since_join = doj,
            ai_tool_uses = uses_ai,
            scraper_tool_uses = uses_web)

@app.route("/prompts", methods=["GET","POST"])
def prompts():
    answer = None
    if request.method == "POST":
        user_prompt = request.form.get("question")
        url = "https://chatgpt-42.p.rapidapi.com/gpt4"

        payload = {
	        "messages": [
		        {
			        "role": "user",
			        "content": user_prompt
		        }
	        ],
	        "web_access": False
        }
        headers = {
	        "x-rapidapi-key": rapidapi_key,
	        "x-rapidapi-host": "chatgpt-42.p.rapidapi.com",
	        "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()
        answer = response_data.get("result")

        promptLog = PromptLog(
            prompt_text = user_prompt,
            generated_output = answer,
            created_by_user_id = session.get("user_id")
        )
        db.session.add(promptLog)
        db.session.commit()

    return render_template("prompts.html", question = answer)


@app.route('/scraper', methods = ["GET", "POST"])
def scraper():
    scraped_content = None
    if request.method == "POST":
        url = request.form.get("url")
        tag = request.form.get("html_tag")

        if not url:
            flash("Please enter a valid URL.", "error")
            return redirect(url_for("web_scraper"))
        
        data = requests.get(url)
 
        soup = BeautifulSoup(data.content, 'html.parser')
        
        tags = soup.find_all(tag)
        scraped_content = [t.text.strip() for t in tags]

        meta_data = {
            "title": soup.title.string if soup.title else "No Title",
            "meta_tags": [
                {"name": tag.get("name", ""), "content": tag.get("content", "")}
                for tag in soup.find_all("meta")
            ]
        }

        scraped_data = ScrapedData(
            url=url,
            content=scraped_content,
            meta_data=json.dumps(meta_data),
            created_by_user_id=session.get("user_id")
        )
        db.session.add(scraped_data)
        db.session.commit()
        flash(f"Content scraped successfully from {url}!", "success")
    
    return render_template("scraper.html", scraped_content = scraped_content)


@app.route("/signup", methods = ["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = bcrypt.generate_password_hash(request.form["passwords"]).decode('utf-8')

        user_exists = User.query.filter_by(email = email).first()
        if user_exists:
            return redirect(url_for('login'))
        

        new_user = User(name = name, email = email, passwords = password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('dashboard'))

    return render_template("signup.html")

@app.route('/success')
def success():
    return "Signup successful! Welcome!"


if __name__ == '__main__':
    app.run()
