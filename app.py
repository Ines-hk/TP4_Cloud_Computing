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

# تحميل المتغيرات من ملف .env
load_dotenv()

app = Flask(__name__)

# ============================================
# 1. Configuration Base de données relationnelle
# ============================================
DATABASE_URL = os.getenv('DATABASE_URL')

def get_db_connection():
    """Retourne une connexion à la base de données (PostgreSQL ou SQLite)"""
    if DATABASE_URL:
        # PostgreSQL (Production)
        return psycopg2.connect(DATABASE_URL)
    else:
        # SQLite (Développement local)
        conn = sqlite3.connect('database.db', timeout=10)
        return conn

def init_database():
    """Créer la table users si elle n'existe pas"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DATABASE_URL:
        # Syntaxe PostgreSQL
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                nom TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    else:
        # Syntaxe SQLite
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
    print(f"✅ Base de données initialisée ({'PostgreSQL' if DATABASE_URL else 'SQLite'})")

def insert_user(nom, email):
    """Insérer un utilisateur dans la base relationnelle"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if DATABASE_URL:
            # PostgreSQL
            cursor.execute(
                'INSERT INTO users (nom, email) VALUES (%s, %s)',
                (nom, email)
            )
        else:
            # SQLite
            cursor.execute(
                'INSERT INTO users (nom, email) VALUES (?, ?)',
                (nom, email)
            )
        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

def get_all_users():
    """Récupérer tous les utilisateurs"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
    users = cursor.fetchall()
    conn.close()
    
    return users

# ============================================
# 2. Configuration MongoDB (NoSQL)
# ============================================
mongo_uri = os.getenv('MONGO_URI')
if not mongo_uri:
    mongo_uri = 'mongodb://localhost:27017'

mongo_client = MongoClient(
    mongo_uri,
    tls=True,
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=5000
)
mongo_db = mongo_client[os.getenv('DATABASE_NAME', 'tp5_cloud')]
logs_collection = mongo_db['logs']

def add_log(action, email):
    """Ajouter un log d'activité dans MongoDB"""
    log_entry = {
        'action': action,
        'email': email,
        'timestamp': datetime.now()
    }
    logs_collection.insert_one(log_entry)
    print(f"📝 Log ajouté: {action} - {email}")

# ============================================
# 3. Routes
# ============================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_user', methods=['POST'])
def add_user():
    nom = request.form['nom']
    email = request.form['email']
    
    # 1. Sauvegarder dans PostgreSQL/SQLite
    success, error = insert_user(nom, email)
    
    if not success:
        if 'UNIQUE constraint failed' in error or 'duplicate key value' in error:
            return """
            <h2 style='color:red;font-family:sans-serif;text-align:center;margin-top:50px;'>
            ❌ Ce courriel est déjà enregistré !<br>
            <a href='/'>Retour</a>
            </h2>
            """
        return f"<h2>Erreur: {error}</h2>"
    
    # 2. Sauvegarder log dans MongoDB
    try:
        add_log('new_user_registered', email)
    except Exception as e:
        print(f"Erreur MongoDB: {e}")
    
    return f"""
    <h2 style='color:green;font-family:sans-serif;text-align:center;margin-top:50px;'>
    ✅ {nom} enregistré avec succès !<br>
    <small>Données sauvegardées dans {'PostgreSQL' if DATABASE_URL else 'SQLite'} et MongoDB</small><br>
    <a href='/'>Retour</a>
    </h2>
    """

@app.route('/users')
def show_users():
    users = get_all_users()
    
    html = f"<h2>Utilisateurs enregistrés ({'PostgreSQL' if DATABASE_URL else 'SQLite'})</h2><ul>"
    for user in users:
        html += f"<li>ID: {user[0]} | Nom: {user[1]} | Email: {user[2]} | Date: {user[3]}</li>"
    html += "</ul><a href='/'>Retour</a>"
    return html

@app.route('/logs')
def show_logs():
    try:
        logs = list(logs_collection.find().sort('timestamp', -1).limit(20))
        html = "<h2>20 derniers logs (MongoDB Atlas)</h2><ul>"
        for log in logs:
            html += f"<li>{log['timestamp']} - {log['action']} - {log['email']}</li>"
        html += "</ul><a href='/'>Retour</a>"
    except Exception as e:
        html = f"<h2>Erreur MongoDB: {str(e)}</h2><a href='/'>Retour</a>"
    return html

# ============================================
# 4. Démarrage
# ============================================
if __name__ == '__main__':
    init_database()
    print(f"✅ MongoDB connecté à: {mongo_uri.split('@')[1] if '@' in mongo_uri else mongo_uri}")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)