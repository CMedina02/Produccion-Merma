from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

DATABASE = 'etiquetas.db'

# Database initialization
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Create suajes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS suajes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            suaje_code TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            cavidades INTEGER NOT NULL,
            separacion_mm REAL NOT NULL,
            tamano_mm REAL NOT NULL
        )
    ''')
    
    # Create usuarios table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # Check if admin user exists
    cursor.execute('SELECT COUNT(*) FROM usuarios WHERE username = ?', ('admin',))
    if cursor.fetchone()[0] == 0:
        # Create default admin user (username: admin, password: admin123)
        hashed_password = generate_password_hash('admin123')
        cursor.execute('INSERT INTO usuarios (username, password) VALUES (?, ?)', ('admin', hashed_password))
    
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Public Routes
@app.route('/')
def index():
    return render_template('calculator.html')

@app.route('/api/suajes')
def get_suajes():
    conn = get_db_connection()
    suajes = conn.execute('SELECT * FROM suajes ORDER BY suaje_code').fetchall()
    conn.close()
    return jsonify([dict(row) for row in suajes])

@app.route('/api/suaje/<suaje_code>')
def get_suaje(suaje_code):
    conn = get_db_connection()
    suaje = conn.execute('SELECT * FROM suajes WHERE suaje_code = ?', (suaje_code,)).fetchone()
    conn.close()
    if suaje:
        return jsonify(dict(suaje))
    return jsonify({'error': 'Suaje no encontrado'}), 404

@app.route('/api/calculate', methods=['POST'])
def calculate():
    data = request.json
    
    try:
        cavidades = float(data['cavidades'])
        separacion_mm = float(data['separacion_mm'])
        tamano_mm = float(data['tamano_mm'])
        millares = float(data['millares'])
        merma = float(data['merma'])
        
        # Formula: (((separacion + tamano) * (millares * 1000)) / cavidades) / 1000
        metros_base = (((separacion_mm + tamano_mm) * (millares * 1000)) / cavidades) / 1000
        metros_con_merma = metros_base * (1 + merma / 100)
        
        return jsonify({
            'metros_base': round(metros_base, 2),
            'metros_con_merma': round(metros_con_merma, 2),
            'merma_aplicada': merma
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Admin Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM usuarios WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada exitosamente', 'success')
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin_dashboard():
    conn = get_db_connection()
    suajes = conn.execute('SELECT * FROM suajes ORDER BY suaje_code').fetchall()
    conn.close()
    return render_template('admin.html', suajes=suajes)

@app.route('/admin/add', methods=['POST'])
@login_required
def admin_add():
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO suajes (suaje_code, nombre, cavidades, separacion_mm, tamano_mm)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            request.form['suaje_code'],
            request.form['nombre'],
            int(request.form['cavidades']),
            float(request.form['separacion_mm']),
            float(request.form['tamano_mm'])
        ))
        conn.commit()
        conn.close()
        flash('Suaje agregado exitosamente', 'success')
    except sqlite3.IntegrityError:
        flash('El código de suaje ya existe', 'error')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit/<int:id>', methods=['POST'])
@login_required
def admin_edit(id):
    try:
        conn = get_db_connection()
        conn.execute('''
            UPDATE suajes 
            SET suaje_code = ?, nombre = ?, cavidades = ?, separacion_mm = ?, tamano_mm = ?
            WHERE id = ?
        ''', (
            request.form['suaje_code'],
            request.form['nombre'],
            int(request.form['cavidades']),
            float(request.form['separacion_mm']),
            float(request.form['tamano_mm']),
            id
        ))
        conn.commit()
        conn.close()
        flash('Suaje actualizado exitosamente', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/<int:id>', methods=['POST'])
@login_required
def admin_delete(id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM suajes WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        flash('Suaje eliminado exitosamente', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
