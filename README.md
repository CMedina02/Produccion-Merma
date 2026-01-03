# ETIQUETAS Y ETIQUETADORAS DEL SURESTE - Calculadora de Material

Aplicación web desarrollada por Eduardo Medina para calcular materiales de producción.

## Características

- **Calculadora Pública**: Interfaz intuitiva para calcular metros de material necesarios
- **Base de Datos**: SQLite con más de 1800 suajes registrados
- **Modo Manual**: Permite cálculos con suajes no registrados
- **Panel de Administración**: CRUD completo para gestionar suajes
- **Diseño Responsivo**: Funciona perfectamente en móviles y PC

## Instalación

### Local

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar aplicación
python app.py
```

La aplicación estará disponible en `http://localhost:5000`

### Despliegue en PythonAnywhere

1. Sube los archivos a tu cuenta de PythonAnywhere
2. Crea un nuevo Web App con Flask
3. Configura el WSGI file para apuntar a `app.py`
4. Instala las dependencias desde requirements.txt
5. Recarga la aplicación

## Uso

### Calculadora Pública

1. Busca el suaje por código o nombre
2. Los datos (cavidades, separación, tamaño) se llenan automáticamente
3. Ingresa la cantidad de millares y porcentaje de merma
4. Haz clic en "Calcular Material"

### Modo Manual

1. Activa el checkbox "¿Suaje no registrado?"
2. Ingresa manualmente: cavidades, separación y tamaño
3. Completa millares y merma
4. Calcula el resultado

### Panel de Administración

- **Usuario por defecto**: admin
- **Contraseña por defecto**: admin123

**IMPORTANTE**: Cambia la contraseña después del primer inicio de sesión.

## Fórmula de Cálculo

```
Metros = (((separación_mm + tamaño_mm) * (millares * 1000)) / cavidades) / 1000
Metros con Merma = Metros * (1 + merma/100)
```

## Seguridad

- Las contraseñas se almacenan con hash usando Werkzeug
- Sesiones protegidas con secret_key
- Acceso administrativo protegido con decorador @login_required

## Tecnologías

- **Backend**: Python 3 + Flask
- **Base de Datos**: SQLite
- **Frontend**: HTML5 + Bootstrap 5 + jQuery + Select2
- **Diseño**: CSS3 personalizado con diseño moderno y profesional
