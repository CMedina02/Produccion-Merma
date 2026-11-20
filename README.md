# Producción Merma

Aplicación web para consultar suajes registrados y estimar el material requerido por millar, incluyendo el porcentaje de merma. El panel administrativo permite gestionar suajes y usuarios.

## Funcionalidades

- Inicio de sesión con contraseñas almacenadas mediante hashes de Werkzeug.
- Consulta de fichas técnicas de suajes desde SQLite.
- Cálculo de metros base y metros con merma.
- Administración de suajes y cuentas con roles `admin` y `operador`.
- Interfaz adaptable a escritorio y móvil.

## Tecnologías

Python 3, Flask, SQLite, pandas (importación CSV), Jinja, Bootstrap, jQuery y Select2.

## Requisitos e inicio local

Se recomienda Python 3.10 o posterior.

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export FLASK_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
python app.py
```

Abre `http://127.0.0.1:5000`. La base existente `etiquetas.db` debe estar presente junto a `app.py`. No ejecutes `crear_db.py` sobre una base existente: el script ahora se detiene sin modificarla. Para inicializar una base nueva, coloca el CSV fuente junto al script y ejecuta `python crear_db.py`; se solicitará una contraseña inicial de al menos 12 caracteres, o puede proporcionarse con `ADMIN_INITIAL_PASSWORD`.

En producción, configura `FLASK_SECRET_KEY` con un secreto aleatorio persistente y `FLASK_ENV=production`; la aplicación falla al iniciar si falta la clave y activa cookies seguras. No reutilices una clave publicada. `FLASK_DEBUG=true` habilita el modo debug solo para desarrollo.

## Estructura

```text
app.py               Rutas Flask, autenticación, API y CRUD
crear_db.py          Inicialización e importación de una base nueva
arreglar_admin.py    Cambio interactivo de contraseña de usuario
templates/           Vistas Jinja
static/              Estilos
etiquetas.db         Base de datos SQLite
BASE SUAJES 2026.csv Fuente de importación de suajes
```

## Ejemplo de uso

1. Inicia sesión con una cuenta existente.
2. Busca un suaje por código o nombre.
3. Indica los millares y el porcentaje de merma.
4. La aplicación calcula `metros_base = millares × metros_x_millar` y `metros_con_merma = metros_base × (1 + merma / 100)`.

## Seguridad y datos

- Las rutas de administración requieren sesión y rol administrador.
- Las consultas SQL usan parámetros para los valores recibidos.
- No se versionan nuevos entornos virtuales, archivos `.env` ni bases SQLite locales por el `.gitignore`.
- La base `etiquetas.db`, el CSV operativo y `venv/` ya están versionados en el repositorio. `.gitignore` no los retira ni elimina sus copias del historial; revisa esos datos y gestiona su exclusión manualmente antes de hacer público el repositorio.
- La base actual fue conservada sin modificaciones por esta revisión. Si conserva la contraseña inicial conocida `admin123`, cámbiala mediante `python arreglar_admin.py` antes de desplegar.

## Limitaciones conocidas

Las operaciones administrativas usan formularios POST, pero aún falta protección CSRF. Antes de exponer el sitio públicamente, agrega y valida protección CSRF para los formularios de administración.
