from django.urls import path

from . import views

urlpatterns = [
    path('', views.reportes, name='reportes'),
    path('exportar/citas.csv', views.exportar_citas_csv, name='exportar_citas_csv'),
    path('exportar/pacientes.csv', views.exportar_pacientes_csv, name='exportar_pacientes_csv'),
]
