# Changelog

Registro técnico de los ajustes realizados al sistema. Formato: archivo — símbolo (clase/función/campo) — qué cambió y por qué.

## 2026-07-03

### `configuration/` (código compartido, nuevo)
- **`configuration/choices.py`** *(archivo nuevo)*: clase `DocType(TextChoices)` con V/E/J/P. Se usa desde `client/models.py` y `user/models.py` para el tipo de documento.
- **`configuration/form_mixins.py`** *(archivo nuevo)*: clase `PlaceholderChoiceMixin` — en `__init__` recorre `self.fields` y a todo `ModelChoiceField` le pone `empty_label = "Seleccione…"` (reemplaza el "---------" de Django). Usado por `PlanForm`, `MembershipForm`, `PaymentForm`, `ClassForm`.
- **`configuration/utils.py`** *(archivo nuevo)*: `paginate(request, queryset, per_page)`, `is_ajax(request)` (chequea el header `X-Requested-With`), `plan_trainer_map_json()` (mapa `{plan_id: requires_trainer}` para el JS de membresías).
- **`configuration/models.py`**: clase abstracta nueva `CreatedByModel` con `created_by = ForeignKey("user.User", null=True, on_delete=SET_NULL, related_name="+")`. Heredada por `Client`, `Membership`, `Freeze`, `Payment`, `Attendance`, `GymClass`, `Plan`, `Service` y `User`.

### `plans/`
- **`plans/models.py`**: `class Plan` pasa a heredar de `CreatedByModel` en vez de `models.Model`.
- **`plans/forms.py`**: `PlanForm` ahora también hereda de `PlaceholderChoiceMixin`.
- **`plans/views.py`**: en `_Page.form_valid()` se agregó `if form.instance.pk is None: form.instance.created_by = self.request.user`. `PlanList.get_queryset()` ya filtraba por `q`; se agregó `get_template_names()` para servir `plans/_results.html` cuando `is_ajax(request)`.
- **`templates/plans/plans.html`**: en el `{% for field in form %}` del modal se agregó la rama `{% if field.name == "included_services" %}`, que envuelve el campo en un checkbox "Es un plan combinado" con `onchange` en JS que muestra/oculta `<div id="combo-services-box">` (antes el checklist de áreas siempre estaba visible).
- **`templates/plans/_results.html`** *(nuevo)*: el bloque `{% for s in areas %}...{% endfor %}` + paginación, extraído de `plans.html` para poder devolverlo solo en las respuestas AJAX del buscador.

### `services/`
- **`services/models.py`**: `class Service` hereda de `CreatedByModel`.
- **`services/views.py`**: `ServiceList.get_queryset()` filtra por `q`; `ServiceList.get_template_names()` (nuevo) devuelve `services/_results.html` en AJAX; `_Page.form_valid()` setea `created_by` igual que en Planes.
- **`templates/services/services.html`**: el loop de campos del form ganó la rama `{% if field.field.widget.input_type == "checkbox" %}` para renderizar `requires_trainer`/`is_active` con la clase `.field-check` en vez de `.input`.
- **`templates/services/_results.html`** *(nuevo)*.

### `user/`
- **`user/models.py`**: se eliminó `discipline = ForeignKey(...)` y se agregó `disciplines = ManyToManyField("services.Service", related_name="instructors")`; se agregó `doc_type = CharField(choices=DocType.choices, default="V")`; `class User(AbstractUser, CreatedByModel)` (herencia múltiple para sumar `created_by`); se agregó la property `full_id`.
- **`user/forms.py`**: `StaffForm` — se agregaron los campos `password1`/`password2` (`CharField(widget=PasswordInput)`); en `__init__` se marcan requeridos solo si `self.instance.pk is None`; en `clean()` se agregó la validación de cédula única por rol (`role`+`doc_type`+`id_card`) y la de contraseñas coincidentes/longitud mínima; se agregó `doc_type` a `Meta.fields`. Clase nueva `ProfileForm` (solo `full_name`, `email`, `phone` + contraseña opcional, sin `role`/`id_card`/`disciplines`).
- **`user/views.py`**: `_Page.form_valid()` ahora llama `obj.set_password(password)` si viene contraseña y setea `created_by` cuando `not obj.username` (indicador de que se está creando); `StaffDelete.form_valid()` ahora emite `messages.success` (antes no avisaba nada al eliminar con éxito); función nueva `profile_edit(request)` (usa `update_session_auth_hash` para no cerrar la sesión al cambiar la contraseña propia); `StaffList.get_queryset()` con filtro `q`; `get_template_names()` para AJAX.
- **`user/urls.py`**: se agregó `path("mi-perfil/", views.profile_edit, name="profile")`.
- **`templates/user/users.html`**: el loop de campos tiene rama especial para `disciplines` (checkboxes en vez de select) y `data-field` en cada div para el JS que muestra/oculta el bloque de disciplinas según el rol elegido.
- **`templates/user/profile.html`** *(nuevo)*: página de "Mi perfil".
- **`templates/user/_results.html`** *(nuevo)*.
- **`templates/base.html`**: el botón "Mi perfil" del menú de usuario ahora apunta a `{% url 'user:profile' %}` en vez de `user:update`.

### `client/`
- **`client/models.py`**:
  - `class Client(CreatedByModel)`: se agregó `doc_type`; se quitó `unique=True` de `id_card` y se agregó `Meta.constraints = [UniqueConstraint(fields=["doc_type","id_card"])]`; `save()` sigue limpiando puntos/guiones de la cédula; se agregó la property `full_id`.
  - Método `freeze(self, reason, kind, amount=None, start=None, user=None)`: antes solo recibía días; ahora recibe `kind` y calcula `end_date` distinto según `Freeze.Kind.DAYS` / `MONTHS` / `INDEFINITE`.
  - Método `unfreeze()`: si el freeze activo era `INDEFINITE`, calcula los días transcurridos desde que se congeló y extiende las membresías esa cantidad.
  - `class Membership(CreatedByModel)`.
  - `class Freeze(CreatedByModel)`: se agregó `kind` (choices DAYS/MONTHS/INDEFINITE); `days` y `end_date` pasan a `null=True`.
- **`client/forms.py`**: `ClientForm.__init__()` — `if self.instance.pk is None: del self.fields["status"]` (oculta el estado al crear, queda Activo por defecto); `clean_id_card()` sigue limpiando puntos/guiones. `MembershipForm.Meta.fields` ya no incluye `start_date` (queda el `default=date.today` del modelo). `FreezeForm` reescrito con `kind` (RadioSelect), `days`, `months` y validación cruzada en `clean()`.
- **`client/views.py`** (el más reescrito de la sesión):
  - Funciones nuevas `_back_url(frm, client)` y `_freeze_ctx(client, form, frm)`.
  - `ClientList.get_context_data()`: soporta `?action=freeze&client=<pk>` para abrir el modal de congelar sobre la lista sin navegar al perfil.
  - `ClientCreate` (antes `View` genérica): en `post()` ahora crea `Client` y `Membership` juntos dentro de un `transaction.atomic()`, seteando `created_by` en ambos.
  - `ClientUpdate` (antes usaba el mixin `_Page` genérico; ahora es clase propia): métodos nuevos `_from()`, `get_template_names()` (elige entre `client/client.html` o `client/detail.html` según de dónde se abrió el editar) y `get_success_url()` — todo basado en el parámetro `from` para volver a la página de origen en vez de siempre ir al listado.
  - Funciones `client_freeze()` y `client_unfreeze()`: ahora leen `frm = request.POST.get("from") or request.GET.get("from") or "detail"` y redirigen con `_back_url(frm, client)`.
  - `membership_add()`: se agregó `m.created_by = request.user`.
- **`templates/client/client.html`**: el botón "Congelar" cambió su `href` de `{% url 'client:detail' c.pk %}?action=freeze` a `{% url 'client:list' %}?action=freeze&client={{ c.pk }}`; el form de "Descongelar" ahora incluye `<input type="hidden" name="from" value="list">`; se agregó `id="clientCreateForm"` y el script que lee `plan_trainer_map_json` para mostrar/ocultar el campo entrenador.
- **`templates/client/detail.html`**: el link "Editar" ahora lleva `?from=detail`; se agregó el bloque `{% if show_form %}` (antes no existía ahí — editar siempre redirigía a `client.html`); el modal de congelar inline se reemplazó por `{% include "client/_freeze_modal.html" %}`.
- **`templates/client/_freeze_modal.html`** *(nuevo)*: modal de congelar compartido entre `client.html` y `detail.html` (antes estaba duplicado/solo en detail).
- **`templates/client/_results.html`** *(nuevo)*.

### `attendance/`
- **`attendance/models.py`**: `class Attendance(CreatedByModel)`.
- **`attendance/urls.py`**: se quitó `path("<int:pk>/eliminar/", views.delete_record, name="delete")`.
- **`attendance/views.py`**: se agregaron los imports `from datetime import datetime` y `time as dt_time` (faltaban; causaban `NameError` silencioso en el bloque que cierra automáticamente entradas abiertas de días anteriores — bug preexistente, no introducido en esta sesión). Se eliminó la función `delete_record`. En `mark_entry()` se cambió `target = normalize_id(doc + number)` + búsqueda sobre `Client.objects.all()` por `target = normalize_id(number)` + `Client.objects.filter(doc_type=doc)` — esto corrige el bug de "no se encuentra" (antes comparaba "V12345678" contra una cédula guardada sin el prefijo "V", nunca podían coincidir). Se agregó `created_by=request.user` en `Attendance.objects.create(...)`. `attendance_list()` ahora soporta `is_ajax` devolviendo `attendance/_results.html`.
- **`templates/attendance/list.html`**: se quitó el botón/form de eliminar de cada fila; se agregó `data-target="search-results"` al form de búsqueda.
- **`templates/attendance/_results.html`** *(nuevo)*.

### `schedules/`
- **`schedules/models.py`**: `class GymClass(CreatedByModel)`; se quitó el campo `block` (CharField con choices fijos tipo "8:40-10:30 am") y se agregaron `start_time`/`end_time` (`TimeField`); se agregaron las constantes `OPEN_TIME = time(5,0)` y `CLOSE_TIME = time(22,0)`; se reescribió `clean()` para validar el rango horario y los solapes por tiempo (`start_time__lt=... end_time__gt=...`) en vez de por igualdad exacta de bloque; se agregó la property `block_label`.
- **`schedules/forms.py`**: `ClassForm.Meta.fields` cambia `"block"` por `"start_time","end_time"`; widgets `TimeInput(attrs={"type":"time","min":"05:00","max":"22:00"})`.
- **`schedules/views.py`**: `_grid()` ahora usa `_hourly_blocks()` (genera 17 bloques de una hora entre 5am-10pm, antes eran 7 bloques fijos hardcodeados); cada celda agrupa clases por rango horario (`block <= c.start_time < next_block`) en vez de por igualdad exacta; se agregó `_format_range()`; `ClassCreate.get_initial()` ahora también pasa `start_time` desde el parámetro `?block=`.
- **`templates/schedules/schedules.html`**: se reescribió la grilla de escritorio y la vista móvil para usar `row.block_label` en vez del string fijo de bloque.
- **`schedules/admin.py`**: `list_display` cambia `"block"` por `"start_time","end_time"`.

### `payments/`
- **`payments/models.py`**: `class Payment(CreatedByModel)`; se agregó `amount_bs = DecimalField(max_digits=12, null=True, blank=True)`.
- **`payments/forms.py`**: `PaymentForm` ahora hereda de `PlaceholderChoiceMixin`; `Meta.fields` agrega `amount_bs`; en `clean()` se reescribió la lógica: si `method == CASH_USD` calcula `amount_bs = amount_usd * rate`; si no, calcula `amount_usd = amount_bs / rate` (usando `GymConfig.load().bcv_rate`); se agregó `_round2()` con `Decimal.quantize`.
- **`payments/views.py`**: se eliminaron por completo las clases `PaymentUpdate` y `PaymentDelete`; se agregó `_renew_membership(client, plan, user)` (busca la membresía del plan, calcula `start = end_date` si sigue vigente o `today` si venció, y aplica `plan.end_date_from(start)`); se separó `_today_ctx` en `_today_stats()` (sin filtro, para las tarjetas de arriba) y `_list_ctx()` (todos los pagos, con búsqueda y `order_by("-created_at")`); `PaymentList.get()` se sobreescribió para servir `payments/_results.html` en AJAX.
- **`payments/urls.py`**: se quitaron las rutas `editar/` y `eliminar/`.
- **`templates/payments/payments.html`**: se quitaron los íconos de editar/eliminar de la tabla y el modal de eliminar completo; el buscador se movió dentro de la tarjeta de la tabla con `data-target="search-results"`.
- **`templates/payments/_results.html`** *(nuevo)*: agrega columna "Fecha" (`{{ p.created_at|date:"d/m/Y g:i A" }}`) y columna "Registrado por".

### `report/`
- **`report/views.py`**: el stat "horario más concurrido" del dashboard usaba `GymClass.objects.values("block")` (campo eliminado); se cambió a `values("start_time","end_time")`.

### `static/css/styles.css`
- Se agregaron `.check-grid`, `.pagination`/`.pg-btn`/`.pg-info`.
- Se quitó `.msg-hide` (ya no se usa: los toasts tienen su propia transición vía `.toast.show`).

### `templates/base.html`
- Se quitó el `document.addEventListener("click", ...)` que cerraba los modales al tocar el fondo.
- El bloque `{% if messages %}` pasó de un `<div id="flashMessages">` con banners fijos a `<div id="toasts">` con `<div class="toast toast-ok/toast-error">` (el CSS de los toasts ya existía pero nunca se había conectado).
- Se reescribió el script de búsqueda: antes hacía `input.form.submit()` (recarga completa); ahora hace `fetch(url, {headers: {"X-Requested-With":"XMLHttpRequest"}})` con debounce y reemplaza `target.innerHTML` del contenedor `data-target` sin recargar la página.

### `templates/_partials/pagination.html` *(nuevo)*
- Partial reutilizable con los controles "‹ Anterior / Página N de M / Siguiente ›", incluido desde cada `_results.html`.

### Datos de prueba
- **`seed_demo_data.sql`** *(archivo nuevo, raíz del proyecto)*: script SQL aditivo (no borra datos reales) que genera ~200 registros por módulo (Servicios, Planes, Usuarios, Clientes+Membresías, Congelaciones, Horarios, Pagos, Asistencia) para probar la app con volumen. Usa IDs fijos en el rango 900001-900200 para no chocar con datos reales, y reinicia las secuencias de PostgreSQL al final para que la app siga generando IDs nuevos sin colisión. Validado ejecutándolo contra la base real dentro de una transacción con rollback.

