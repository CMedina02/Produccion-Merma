"""Actualiza de forma interactiva la contraseña de una cuenta existente."""
import getpass
import os
import sqlite3

from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'etiquetas.db')


def arreglar_password():
    usuario = input('Nombre de usuario que se actualizará: ').strip()
    if not usuario:
        print('ERROR: El nombre de usuario no puede estar vacío.')
        return
    nueva_contrasena = getpass.getpass('Nueva contraseña (mínimo 12 caracteres): ')
    if len(nueva_contrasena) < 12:
        print('ERROR: La contraseña debe tener al menos 12 caracteres.')
        return
    confirmacion = getpass.getpass('Confirma la nueva contraseña: ')
    if nueva_contrasena != confirmacion:
        print('ERROR: Las contraseñas no coinciden.')
        return

    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.execute(
                'UPDATE usuarios SET password = ? WHERE username = ?',
                (generate_password_hash(nueva_contrasena), usuario),
            )
        if cursor.rowcount:
            print(f"Contraseña actualizada para '{usuario}'.")
        else:
            print(f"No se encontró al usuario '{usuario}'.")
    except sqlite3.Error as error:
        print(f'Error de base de datos: {error}')


if __name__ == '__main__':
    arreglar_password()
