import hashlib
import os
import sqlite3
import tempfile
import unittest

import app as webapp
from werkzeug.security import generate_password_hash


class ApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.operational_db = webapp.DATABASE
        with open(cls.operational_db, 'rb') as source:
            cls.operational_hash = hashlib.sha256(source.read()).hexdigest()

    def setUp(self):
        handle, self.db_path = tempfile.mkstemp(suffix='.sqlite3')
        os.close(handle)
        webapp.DATABASE = self.db_path
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
                     ('admin', generate_password_hash('admin-password'), 'admin'))
        conn.execute('INSERT INTO usuarios VALUES (2, ?, ?, ?)',
                     ('operador', generate_password_hash('operador-password'), 'operador'))
        conn.execute('INSERT INTO suajes VALUES (1, ?, ?, 10, ?, 1, 1, 1, 1, 1, 1, 8.5)',
                     ('S-1', 'Demo', 'papel'))
        conn.commit()
        conn.close()
        webapp.app.config.update(TESTING=True, SECRET_KEY='test-secret')
        self.client = webapp.app.test_client()

    def tearDown(self):
        webapp.DATABASE = self.operational_db
        os.unlink(self.db_path)

    def token(self):
        with self.client.session_transaction() as session:
            token = session.get('_csrf_token')
        if token is None:
            self.client.get('/login')
            with self.client.session_transaction() as session:
                token = session['_csrf_token']
        return token

    def login(self, username='admin', password='admin-password'):
        return self.client.post('/login', data={
            'username': username, 'password': password, 'csrf_token': self.token()
        })

    def test_login_valid_invalid_and_csrf(self):
        self.assertEqual(self.client.post('/login', data={'username': 'admin'}).status_code, 400)
        self.assertEqual(self.login('admin', 'wrong').status_code, 200)
        response = self.login()
        self.assertEqual(response.status_code, 302)
        self.client.get('/logout')
        response = self.login('admin', 'admin-password')
        self.assertEqual(response.status_code, 302)

    def test_authentication_role_and_calculation(self):
        self.assertEqual(self.client.get('/').status_code, 302)
        self.login('operador', 'operador-password')
        self.assertEqual(self.client.get('/admin').status_code, 302)
        result = self.client.post('/api/calculate', json={'suaje_id': 1, 'millares': 2, 'merma': 10})
        self.assertEqual(result.json, {'metros_base': 17.0, 'metros_con_merma': 18.7})
        invalid = self.client.post('/api/calculate', json={'suaje_id': 1, 'millares': -1, 'merma': 10})
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(self.client.post('/api/calculate', json={'suaje_id': 1, 'millares': 'NaN', 'merma': 1}).status_code, 400)

    def test_admin_crud_requires_csrf_and_works_with_token(self):
        self.login()
        self.assertEqual(self.client.post('/admin/users/add', data={'username': 'x', 'password': 'x', 'role': 'operador'}).status_code, 400)
        data = {
            'csrf_token': self.token(), 'suaje_code': 'S-2', 'nombre': 'Nuevo', 'dientes': '4',
            'material': 'papel', 'metros_x_millar': '3.5', 'med_eje_mm': '1', 'med_des_mm': '1',
            'cav_eje': '1', 'cav_des': '1', 'sep_eje_mm': '1', 'sep_des_mm': '1'
        }
        self.assertEqual(self.client.post('/admin/add', data=data).status_code, 302)
        data['nombre'] = 'Editado'
        self.assertEqual(self.client.post('/admin/edit/1', data=data).status_code, 302)
        self.assertEqual(self.client.post('/admin/delete/2', data={'csrf_token': self.token()}).status_code, 302)
        self.assertEqual(self.client.post('/admin/users/add', data={
            'csrf_token': self.token(), 'username': 'nuevo', 'password': 'clave', 'role': 'operador'
        }).status_code, 302)
        self.assertEqual(self.client.post('/admin/users/delete/2', data={'csrf_token': self.token()}).status_code, 302)

    @classmethod
    def tearDownClass(cls):
        with open(cls.operational_db, 'rb') as source:
            assert hashlib.sha256(source.read()).hexdigest() == cls.operational_hash


if __name__ == '__main__':
    unittest.main()
