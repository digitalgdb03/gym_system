# Zona Gym — Sistema de gestión (Django)

Sistema administrativo para gimnasio con doble precio (BCV / Divisas), interfaz en
español, gestión de clientes, membresías, congelaciones, planes, servicios, clases,
pagos, asistencia y reportes.

## Requisitos
- Python 3.11+
- (Opcional) PostgreSQL. En desarrollo usa SQLite sin configuración extra.

## Puesta en marcha
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # ajusta SECRET_KEY, DEBUG, DATABASE_URL

python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser   # crea el usuario que inicia sesión
python manage.py runserver
```

Antes de correr, coloca tu `styles.css` en `static/css/` y `zona_gym.png` en `static/images/`.

## Apps
- **configuration** — config global (nombre, tasa BCV) singleton + filtros de plantilla.
- **services** — áreas (OPEN / GUIDED / MIXED).
- **plans** — planes con doble precio y combos.
- **user** — usuario custom (AbstractUser): administrador, empleado, instructor.
- **client** — clientes, membresías, congelación.
- **schedules** — calendario semanal de clases.
- **payments** — pagos (moneda derivada del método).
- **attendance** — marcaje por cédula con alerta de estatus.
- **report** — dashboard y reportes (día / semana / mes).

Nota: `AUTH_USER_MODEL = "user.User"` ya está fijado en settings; no cambia tras migrar.
