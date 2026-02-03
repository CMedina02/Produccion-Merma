from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3
import os
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'clave-super-secreta-2026'

# Configuración Base de Datos Local
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'etiquetas.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# --- DECORADORES DE SEGURIDAD ---

# 1. Login Requerido (Bloquea acceso a no registrados)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# 2. Solo Admin (Bloquea acceso a operadores normales)
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Acceso denegado. Se requieren permisos de administrador.', 'error')
            # Si intenta entrar a admin y no es admin, lo mandamos a la calculadora
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# --- RUTAS PÚBLICAS / LOGIN ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Si ya está logueado, redirigir según su rol
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM usuarios WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role'] # Guardamos el rol (admin/operador)
            
            # REDIRECCIÓN INTELIGENTE
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- RUTAS DE LA APP (CALCULADORA) ---

@app.route('/')
@login_required  # <--- AHORA ESTÁ PROTEGIDA
def index():
    # Pasamos el rol a la plantilla por si queremos mostrar botones extra al admin
    return render_template('calculator.html', user_role=session.get('role'))

@app.route('/api/suajes')
@login_required
def get_suajes():
    try:
        conn = get_db_connection()
        query = '''
            SELECT id, suaje_code, nombre, dientes, material, 
                   med_eje_mm, med_des_mm, cav_eje, cav_des, 
                   sep_eje_mm, sep_des_mm, metros_x_millar 
            FROM suajes ORDER BY suaje_code
        '''
        suajes = conn.execute(query).fetchall()
        conn.close()
        return jsonify([dict(row) for row in suajes])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/calculate', methods=['POST'])
@login_required
def calculate():
    data = request.json
    try:
        millares = float(data.get('millares', 0))
        merma = float(data.get('merma', 0))
        suaje_id = data.get('suaje_id')
        
        conn = get_db_connection()
        suaje = conn.execute('SELECT metros_x_millar FROM suajes WHERE id = ?', (suaje_id,)).fetchone()
        conn.close()

        if not suaje: return jsonify({'error': 'Suaje no encontrado'}), 404

        factor = float(suaje['metros_x_millar'])
        
        # FÓRMULA 2026
        metros_base = millares * factor
        metros_total = metros_base * (1 + merma / 100)

        return jsonify({
            'metros_base': round(metros_base, 2),
            'metros_con_merma': round(metros_total, 2)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# --- PANEL DE ADMINISTRADOR ---

@app.route('/admin')
@login_required
@admin_required # <--- SOLO ADMIN PUEDE ENTRAR
def admin_dashboard():
    conn = get_db_connection()
    suajes = conn.execute('SELECT * FROM suajes ORDER BY suaje_code').fetchall()
    usuarios = conn.execute('SELECT * FROM usuarios ORDER BY username').fetchall() # Cargar usuarios para la lista
    conn.close()
    return render_template('admin.html', suajes=suajes, usuarios=usuarios)

# GESTIÓN DE SUAJES (CRUD)
@app.route('/admin/add', methods=['POST'])
@admin_required
def admin_add():
    try:
        conn = get_db_connection()
        def get_float(k): return float(request.form.get(k) or 0)
        def get_int(k): return int(request.form.get(k) or 0)
        
        conn.execute('''
            INSERT INTO suajes (
                suaje_code, nombre, dientes, material, metros_x_millar, 
                med_eje_mm, med_des_mm, cav_eje, cav_des, sep_eje_mm, sep_des_mm
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request.form['suaje_code'], request.form['nombre'], get_int('dientes'), request.form['material'],
            get_float('metros_x_millar'), get_float('med_eje_mm'), get_float('med_des_mm'),
            get_int('cav_eje'), get_int('cav_des'), get_float('sep_eje_mm'), get_float('sep_des_mm')
        ))
        conn.commit()
        conn.close()
        flash('Suaje agregado correctamente', 'success')
    except sqlite3.IntegrityError:
        flash('El código de suaje ya existe', 'error')
    except Exception as e:
        flash(f'Error al guardar: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit/<int:id>', methods=['POST'])
@admin_required
def admin_edit(id):
    try:
        conn = get_db_connection()
        def get_float(k): return float(request.form.get(k) or 0)
        def get_int(k): return int(request.form.get(k) or 0)

        conn.execute('''
            UPDATE suajes SET 
                suaje_code=?, nombre=?, dientes=?, material=?, metros_x_millar=?, 
                med_eje_mm=?, med_des_mm=?, cav_eje=?, cav_des=?, sep_eje_mm=?, sep_des_mm=?
            WHERE id=?
        ''', (
            request.form['suaje_code'], request.form['nombre'], get_int('dientes'), request.form['material'],
            get_float('metros_x_millar'), get_float('med_eje_mm'), get_float('med_des_mm'),
            get_int('cav_eje'), get_int('cav_des'), get_float('sep_eje_mm'), get_float('sep_des_mm'), id
        ))
        conn.commit()
        conn.close()
        flash('Suaje actualizado correctamente', 'success')
    except Exception as e:
        flash(f'Error al actualizar: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/<int:id>', methods=['POST'])
@admin_required
def admin_delete(id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM suajes WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        flash('Suaje eliminado', 'success')
    except:
        flash('Error al eliminar', 'error')
    return redirect(url_for('admin_dashboard'))

# --- GESTIÓN DE USUARIOS (NUEVO) ---

@app.route('/admin/users/add', methods=['POST'])
@admin_required
def user_add():
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']
    
    if not username or not password:
        flash('Faltan datos', 'error')
        return redirect(url_for('admin_dashboard'))

    hashed_pw = generate_password_hash(password)
    
    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)', 
                     (username, hashed_pw, role))
        conn.commit()
        conn.close()
        flash(f'Usuario {username} creado exitosamente', 'success')
    except sqlite3.IntegrityError:
        flash('El nombre de usuario ya existe', 'error')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/users/delete/<int:id>', methods=['POST'])
@admin_required
def user_delete(id):
    # Protección: No te puedes borrar a ti mismo si estás logueado
    if id == session.get('user_id'):
        flash('No puedes eliminar tu propia cuenta mientras estás en uso.', 'error')
        return redirect(url_for('admin_dashboard'))
        
    conn = get_db_connection()
    conn.execute('DELETE FROM usuarios WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Usuario eliminado', 'success')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)