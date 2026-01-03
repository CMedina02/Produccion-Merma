import sqlite3
from werkzeug.security import generate_password_hash

# Configuración
nombre_db = 'etiquetas.db'
usuario = 'admin'
nueva_contrasena = 'admin123' # La contraseña que quieres usar

def arreglar_password():
    try:
        # 1. Conectar a la base de datos
        conn = sqlite3.connect(nombre_db)
        cursor = conn.cursor()

        # 2. Generar el hash seguro (encriptación)
        password_encriptada = generate_password_hash(nueva_contrasena)

        # 3. Actualizar el usuario admin
        cursor.execute("UPDATE usuarios SET password = ? WHERE username = ?", 
                       (password_encriptada, usuario))
        
        if cursor.rowcount > 0:
            print(f"✅ ¡Éxito! La contraseña del usuario '{usuario}' ha sido actualizada y encriptada.")
            print(f"   Nueva contraseña para entrar: {nueva_contrasena}")
        else:
            print(f"⚠️ No se encontró al usuario '{usuario}'. ¿Seguro que existe?")

        conn.commit()
        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    arreglar_password()