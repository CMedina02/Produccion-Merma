import sqlite3
import pandas as pd
import os
import re
import getpass
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, 'BASE SUAJES 2026.csv')
DATABASE = os.path.join(BASE_DIR, 'etiquetas.db')

def correccion_lexica(texto):
    """
    Corrige palabras completas basándose en patrones conocidos de la industria.
    """
    if not isinstance(texto, str):
        return texto

    texto_out = texto.upper()

    # 1. DICCIONARIO DE PALABRAS COMUNES
    correcciones = {
        r'JAB.*?N': 'JABÓN',
        r'L.*?QUIDO': 'LÍQUIDO',
        r'A.*?OS': 'AÑOS',
        r'TAMA.*?O': 'TAMAÑO',
        r'DISE.*?O': 'DISEÑO',
        r'PEQUE.*?O': 'PEQUEÑO',
        r'GARANT.*?A': 'GARANTÍA',
        r'T.*?RMICA': 'TÉRMICA',
        r'EL.*?CTRICO': 'ELÉCTRICO',
        r'PL.*?STICO': 'PLÁSTICO',
        r'IMPRESI.*?N': 'IMPRESIÓN',
        r'PR.*?CTICO': 'PRÁCTICO',
        r'AUTOM.*?TICO': 'AUTOMÁTICO'
    }

    for patron, correcta in correcciones.items():
        texto_out = re.sub(patron, correcta, texto_out)

    # 2. LIMPIEZA DE CARACTERES SUELTOS
    reemplazos_basicos = {
        'ï»¿': '', 'Â': '', 'Ã': 'Í', 'ï¿½': ''
    }
    for malo, bueno in reemplazos_basicos.items():
        texto_out = texto_out.replace(malo, bueno)

    return texto_out.strip()

def encontrar_columna(df, palabras_clave):
    """Busca columnas por palabras clave."""
    for col in df.columns:
        nombre_limpio = str(col).lower().replace('.', '').replace(' ', '')
        if all(p.lower() in nombre_limpio for p in palabras_clave):
            return col
    return None

def crear_base_datos():
    print(">>> INICIANDO IMPORTACIÓN CON SISTEMA DE ROLES")

    if not os.path.exists(CSV_FILE):
        print(f"ERROR: No se encuentra {CSV_FILE}")
        return

    # 1. LEER ARCHIVO
    print("Lectura del archivo...")
    try:
        df = pd.read_csv(CSV_FILE, encoding='latin1')
    except:
        df = pd.read_csv(CSV_FILE, encoding='utf-8')

    # 2. MAPEO DE COLUMNAS
    print("Mapeando columnas...")
    mapa = {
        'codigo': ['suaje'],
        'nombre': ['nombre'],
        'dientes': ['dientes'],
        'material': ['material'],
        'factor': ['metros', 'millar'],
        'med_eje': ['med', 'eje'],
        'med_des': ['med', 'des'],
        'cav_eje': ['cav', 'eje'],
        'cav_des': ['cav', 'des'],
        'sep_eje': ['sep', 'eje'],
        'sep_des': ['sep', 'des']
    }

    cols = {}
    for k, v in mapa.items():
        found = encontrar_columna(df, v)
        if found: cols[k] = found

    if 'codigo' not in cols:
        print("ERROR CRITICO: No se encontró columna 'Suaje'.")
        return

    # Nunca sobrescribir una base existente: puede contener datos operativos.
    if os.path.exists(DATABASE):
        print(f"ERROR: {DATABASE} ya existe. No se modificó.")
        return
    password = os.environ.get('ADMIN_INITIAL_PASSWORD') or getpass.getpass(
        'Contraseña para la cuenta administradora inicial: '
    )
    if len(password) < 12:
        print('ERROR: La contraseña inicial debe tener al menos 12 caracteres.')
        return

    # 3. CREAR BASE DE DATOS
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # --- TABLA DE USUARIOS CON ROLES ---
    cursor.execute('''
        CREATE TABLE usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'operador' 
        )
    ''')
    
    # Creamos el SUPER ADMIN por defecto
    cursor.execute("INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)",
                   ('admin', generate_password_hash(password), 'admin'))
    
    print("✅ Usuario 'admin' creado con privilegios de administrador.")

    # --- TABLA DE SUAJES (11 Columnas) ---
    cursor.execute('''
        CREATE TABLE suajes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            suaje_code TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            dientes INTEGER DEFAULT 0,
            material TEXT DEFAULT '',
            med_eje_mm REAL DEFAULT 0,
            med_des_mm REAL DEFAULT 0,
            cav_eje INTEGER DEFAULT 0,
            cav_des INTEGER DEFAULT 0,
            sep_eje_mm REAL DEFAULT 0,
            sep_des_mm REAL DEFAULT 0,
            metros_x_millar REAL DEFAULT 0
        )
    ''')

    # 4. INSERTAR Y CORREGIR DATOS
    print("Insertando y corrigiendo textos...")
    count = 0
    
    for _, row in df.iterrows():
        try:
            raw_code = row[cols['codigo']]
            codigo = str(raw_code).strip()
            
            if not codigo or codigo.lower() == 'nan': continue

            def get_num(key, is_int=False):
                if key not in cols: return 0
                val = row[cols[key]]
                try:
                    num = float(str(val).replace(',', ''))
                    return int(num) if is_int else num
                except: return 0

            # Corrección Léxica
            nombre_raw = str(row[cols.get('nombre', '')]) if 'nombre' in cols else ''
            material_raw = str(row[cols.get('material', '')]) if 'material' in cols else ''
            
            nombre_final = correccion_lexica(nombre_raw)
            material_final = correccion_lexica(material_raw)

            cursor.execute('''
                INSERT INTO suajes (
                    suaje_code, nombre, dientes, material,
                    med_eje_mm, med_des_mm, cav_eje, cav_des,
                    sep_eje_mm, sep_des_mm, metros_x_millar
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                correccion_lexica(codigo),
                nombre_final,
                get_num('dientes', True),
                material_final,
                get_num('med_eje'),
                get_num('med_des'),
                get_num('cav_eje', True),
                get_num('cav_des', True),
                get_num('sep_eje'),
                get_num('sep_des'),
                get_num('factor')
            ))
            count += 1
        except Exception:
            pass

    conn.commit()
    conn.close()
    print(f"RESUMEN: {count} registros importados. Base de datos con roles lista.")

if __name__ == '__main__':
    crear_base_datos()
