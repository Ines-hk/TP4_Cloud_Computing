

from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# تحميل المتغيرات من ملف .env
load_dotenv()

app = Flask(__name__)

# ============================================
# 1. Configuration PostgreSQL (Relationnelle)
# ============================================
def get_db_connection():
    """إنشاء اتصال بقاعدة PostgreSQL"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        # fallback to SQLite for local development
        return None
    return psycopg2.connect(database_url)

def init_postgresql():
    """إنشاء جدول المستخدمين إذا لم يكن موجوداً"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        # استخدام SQLite محلياً
        conn = sqlite3.connect('database.db', timeout=10)
        cursor = conn.cursor()
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
        return
    
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            nom TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    
# ============================================
# 2. Configuration MongoDB (NoSQL)
# ============================================
# الاتصال بـ MongoDB المحلي
# الاتصال بـ MongoDB Atlas مع دعم SSL
import certifi
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
    """إضافة سجل نشاط في MongoDB"""
    log_entry = {
        'action': action,
        'email': email,
        'timestamp': datetime.now()
    }
    logs_collection.insert_one(log_entry)

# ============================================
# 3. Routes (المسارات)
# ============================================
@app.route('/')
def index():
    """الصفحة الرئيسية - عرض نموذج التسجيل"""
    return render_template('index.html')

@app.route('/add_user', methods=['POST'])
def add_user():
    """استقبال بيانات المستخدم وحفظها في القاعدتين"""
    if request.method == 'POST':
        nom = request.form['nom']
        email = request.form['email']
        
        try:
            # الخطوة 1: حفظ في SQLite (قاعدة علائقية)
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (nom, email) VALUES (?, ?)', (nom, email))
            conn.commit()
            conn.close()
            
            # الخطوة 2: حفظ log في MongoDB (قاعدة NoSQL)
            add_log('new_user_registered', email)
            
            # رسالة نجاح (يمكن تحسينها لاحقاً)
            return f"""
            <h2 style='color:green;font-family:sans-serif;text-align:center;margin-top:50px;'>
            ✅ تم تسجيل {nom} بنجاح!<br>
            <small>تم الحفظ في SQLite و MongoDB معاً</small><br>
            <a href='/'>العودة للصفحة الرئيسية</a>
            </h2>
            """
            
        except sqlite3.IntegrityError:
            return """
            <h2 style='color:red;font-family:sans-serif;text-align:center;margin-top:50px;'>
            ❌ هذا البريد الإلكتروني مسجل مسبقاً!<br>
            <a href='/'>العودة للصفحة الرئيسية</a>
            </h2>
            """
        except Exception as e:
            return f"<h2>حدث خطأ: {str(e)}</h2>"

@app.route('/users')
def show_users():
    """عرض جميع المستخدمين المسجلين في SQLite"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
    users = cursor.fetchall()
    conn.close()
    
    html = "<h2>المستخدمون المسجلون (SQLite)</h2><ul>"
    for user in users:
        html += f"<li>ID: {user[0]} | الاسم: {user[1]} | البريد: {user[2]} | التاريخ: {user[3]}</li>"
    html += "</ul><a href='/'>العودة</a>"
    return html

@app.route('/logs')
def show_logs():
    """عرض سجلات MongoDB"""
    logs = list(logs_collection.find().sort('timestamp', -1).limit(20))
    
    html = "<h2>آخر 20 نشاط (MongoDB)</h2><ul>"
    for log in logs:
        html += f"<li>{log['timestamp']} - {log['action']} - {log['email']}</li>"
    html += "</ul><a href='/'>العودة</a>"
    return html

# ============================================
# 4. نقطة البداية
# ============================================
if __name__ == '__main__':
    # تهيئة قاعدة البيانات SQLite عند التشغيل
    init_sqlite()
    print("✅ تم تهيئة SQLite (database.db)")
    print("✅ MongoDB متصل على:", mongo_uri)
    print("🚀 التطبيق يعمل على: http://127.0.0.1:5000")
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
