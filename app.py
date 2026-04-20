# ============================================
# TP5 Cloud Computing - Application Hybride
# PostgreSQL (Relationnel) + MongoDB (NoSQL)
# ============================================

from flask import Flask, render_template, request
import sqlite3
import psycopg2
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv
import certifi

load_dotenv()
app = Flask(__name__)

DATABASE_URL = os.getenv('DATABASE_URL')

def get_db_connection():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    else:
        conn = sqlite3.connect('database.db', timeout=10)
        return conn

def ensure_table_exists():
    """S'assure que la table users existe AVANT chaque opération"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DATABASE_URL:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                nom TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    conn.commit()
    conn.close()

def insert_user(nom, email):
    ensure_table_exists()  # Crée la table si elle n'existe pas
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if DATABASE_URL:
            cursor.execute('INSERT INTO users (nom, email) VALUES (%s, %s)', (nom, email))
        else:
            cursor.execute('INSERT INTO users (nom, email) VALUES (?, ?)', (nom, email))
        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

def get_all_users():
    ensure_table_exists()  # Crée la table si elle n'existe pas
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
    users = cursor.fetchall()
    conn.close()
    return users

# MongoDB
mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
mongo_client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
mongo_db = mongo_client[os.getenv('DATABASE_NAME', 'tp5_cloud')]
logs_collection = mongo_db['logs']

def add_log(action, email):
    logs_collection.insert_one({'action': action, 'email': email, 'timestamp': datetime.now()})

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_user', methods=['POST'])
def add_user():
    nom = request.form['nom']
    email = request.form['email']
    
    success, error = insert_user(nom, email)
    
    if not success:
        if 'UNIQUE' in error.upper():
            return "<h2 style='color:red;text-align:center;'>❌ Email déjà enregistré !<br><a href='/'>Retour</a></h2>"
        return f"<h2>Erreur: {error}</h2>"
    
    try:
        add_log('new_user_registered', email)
    except:
        pass
    
    return f"<h2 style='color:green;text-align:center;'>✅ {nom} enregistré !<br><a href='/'>Retour</a></h2>"

@app.route('/users')
def show_users():
    users = get_all_users()
    html = "<h2>Utilisateurs</h2><ul>"
    for u in users:
        html += f"<li>{u[1]} - {u[2]}</li>"
    html += "</ul><a href='/'>Retour</a>"
    return html

@app.route('/logs')
def show_logs():
    try:
        logs = list(logs_collection.find().limit(20))
        # ترتيب في Python بدل MongoDB
        logs.sort(key=lambda x: x.get('timestamp', datetime.min), reverse=True)
        
        html = "<h2>Logs MongoDB</h2><ul>"
        for l in logs:
            html += f"<li>{l.get('timestamp', 'N/A')} - {l.get('action', 'N/A')} - {l.get('email', 'N/A')}</li>"
        html += "</ul><a href='/'>Retour</a>"
        return html
    except Exception as e:
        return f"<h2>Erreur MongoDB: {e}</h2>"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)