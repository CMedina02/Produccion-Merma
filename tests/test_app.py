import os
import secrets
import sqlite3
import tempfile
import unittest

import app as webapp
from werkzeug.security import generate_password_hash


class ApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_database = webapp.DATABASE

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.addCleanup(setattr, webapp, 'DATABASE', self.original_database)
        self.db_path = os.path.join(self.temp_dir.name, 'test.sqlite3')
        webapp.DATABASE = self.db_path
        self.admin_password = secrets.token_urlsafe(24)
        self.operator_password = secrets.token_urlsafe(24)
        conn = sqlite3.connect(self.db_path)
        conn.executescript('''
            CREATE TABLE usuarios (id INTEGER PRIMARY KEY, username TEXT UNIQUE,
                password TEXT, role TEXT);
            CREATE TABLE suajes (id INTEGER PRIMARY KEY, suaje_code TEXT UNIQUE,
                nombre TEXT, dientes INTEGER, material TEXT, med_eje_mm REAL,
                med_des_mm REAL, cav_eje INTEGER, cav_des INTEGER,
                sep_eje_mm REAL, sep_des_mm REAL, metros_x_millar REAL);
        ''')
        conn.execute('INSERT INTO usuarios VALUES (1, ?, ?, ?)',
                     ('admin', generate_password_hash(self.admin_password), 'admin'))
        conn.execute('INSERT INTO usuarios VALUES (2, ?, ?, ?)',
                     ('operador', generate_password_hash(self.operator_password), 'operador'))
        conn.execute('INSERT INTO suajes VALUES (1, ?, ?, 10, ?, 1, 1, 1, 1, 1, 1, 8.5)',
                     ('S-1', 'Demo', 'papel'))
        conn.commit()
        conn.close()
        webapp.app.config.update(TESTING=True, SECRET_KEY=secrets.token_hex(32))
        self.client = webapp.app.test_client()

    def token(self):
        with self.client.session_transaction() as session:
            token = session.get('_csrf_token')
        if token is None:
            self.client.get('/login')
            with self.client.session_transaction() as session:
                token = session['_csrf_token']
        return token

    def login(self, username='admin', password=None):
        if password is None:
            password = self.admin_password if username == 'admin' else self.operator_password
        return self.client.post('/login', data={
            'username': username, 'password': password, 'csrf_token': self.token()
        })

    def test_default_configuration_and_sqlite_runtime(self):
        self.assertFalse(webapp.app.config['DEBUG'])
        self.assertTrue(webapp.app.config['SECRET_KEY'])
        self.assertTrue(sqlite3.sqlite_version)
        self.assertEqual(self.client.get('/login').status_code, 200)

    def test_login_valid_invalid_and_csrf(self):
        page = self.client.get('/login')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'name="csrf_token"', page.data)
        self.assertEqual(self.client.post('/login', data={'username': 'admin'}).status_code, 400)
        self.assertEqual(self.client.post('/login', data={
            'username': 'admin', 'password': self.admin_password, 'csrf_token': 'invalid'
        }).status_code, 400)
        self.assertEqual(self.login('admin', secrets.token_urlsafe(16)).status_code, 200)
        response = self.login()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get('/').status_code, 200)
        logout = self.client.get('/logout')
        self.assertEqual(logout.status_code, 302)
        self.assertEqual(self.client.get('/').status_code, 302)
        self.assertEqual(self.login().status_code, 302)

    def test_authentication_role_and_calculation(self):
        self.assertEqual(self.client.get('/').status_code, 302)
        self.assertEqual(self.client.get('/admin').status_code, 302)
        self.login('operador')
        self.assertEqual(self.client.get('/admin').status_code, 302)
        self.assertEqual(self.client.post('/admin/add', data={'csrf_token': self.token()}).status_code, 302)
        result = self.client.post('/api/calculate', json={'suaje_id': 1, 'millares': 2, 'merma': 10})
        self.assertEqual(result.json, {'metros_base': 17.0, 'metros_con_merma': 18.7})
        invalid = self.client.post('/api/calculate', json={'suaje_id': 1, 'millares': -1, 'merma': 10})
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(self.client.post('/api/calculate', json={'suaje_id': 1, 'millares': 'NaN', 'merma': 1}).status_code, 400)

    def test_admin_crud_requires_csrf_and_works_with_token(self):
        self.login()
        self.assertEqual(self.client.post('/admin/add', data={}).status_code, 400)
        self.assertEqual(self.client.post('/admin/users/add', data={
            'username': 'sin-csrf', 'password': secrets.token_urlsafe(16), 'role': 'operador'
        }).status_code, 400)
        data = {
            'csrf_token': self.token(), 'suaje_code': 'S-2', 'nombre': 'Nuevo', 'dientes': '4',
            'material': 'papel', 'metros_x_millar': '3.5', 'med_eje_mm': '1', 'med_des_mm': '1',
            'cav_eje': '1', 'cav_des': '1', 'sep_eje_mm': '1', 'sep_des_mm': '1'
        }
        self.assertEqual(self.client.post('/admin/add', data=data).status_code, 302)
        with sqlite3.connect(self.db_path) as conn:
            self.assertEqual(conn.execute('SELECT suaje_code FROM suajes WHERE id = 2').fetchone()[0], 'S-2')
        data['suaje_code'] = 'S-1-edit'
        data['nombre'] = 'Editado'
        self.assertEqual(self.client.post('/admin/edit/1', data=data).status_code, 302)
        with sqlite3.connect(self.db_path) as conn:
            self.assertEqual(conn.execute('SELECT nombre FROM suajes WHERE id = 1').fetchone()[0], 'Editado')
        self.assertEqual(self.client.post('/admin/delete/2', data={'csrf_token': self.token()}).status_code, 302)
        with sqlite3.connect(self.db_path) as conn:
            self.assertIsNone(conn.execute('SELECT id FROM suajes WHERE id = 2').fetchone())
        self.assertEqual(self.client.post('/admin/users/add', data={
            'csrf_token': self.token(), 'username': 'nuevo', 'password': secrets.token_urlsafe(16), 'role': 'operador'
        }).status_code, 302)
        with sqlite3.connect(self.db_path) as conn:
            self.assertEqual(conn.execute('SELECT role FROM usuarios WHERE username = ?', ('nuevo',)).fetchone()[0], 'operador')
        self.assertEqual(self.client.post('/admin/users/delete/2', data={'csrf_token': self.token()}).status_code, 302)
        with sqlite3.connect(self.db_path) as conn:
            self.assertIsNone(conn.execute('SELECT id FROM usuarios WHERE id = 2').fetchone())

if __name__ == '__main__':
    unittest.main()
