from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", include("report.urls")),            # dashboard / home
    path("configuracion/", include("configuration.urls")),
    path("servicios/", include("services.urls")),
    path("planes/", include("plans.urls")),
    path("usuarios/", include("user.urls")),
    path("clientes/", include("client.urls")),
    path("horarios/", include("schedules.urls")),
    path("pagos/", include("payments.urls")),
    path("asistencias/", include("attendance.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
