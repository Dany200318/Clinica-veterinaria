from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

admin.site.site_header = 'Clínica Veterinaria — Administración'
admin.site.site_title = 'Clínica Veterinaria'
admin.site.index_title = 'Panel de administración de Django'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='dashboard', permanent=False), name='inicio'),
    path('admin/', admin.site.urls),
    path('', include('usuarios.urls')),
    path('pacientes/', include('pacientes.urls')),
    path('citas/', include('citas.urls')),
    path('notificaciones/', include('notificaciones.urls')),
    path('reportes/', include('reportes.urls')),
]
