from django.urls import path

from . import views

urlpatterns = [
    # Búsqueda general (RF-07)
    path('buscar/', views.buscar, name='buscar'),

    # Propietarios (RF-05)
    path('propietarios/', views.lista_propietarios, name='lista_propietarios'),
    path('propietarios/nuevo/', views.crear_propietario, name='crear_propietario'),
    path('propietarios/<int:pk>/', views.detalle_propietario, name='detalle_propietario'),
    path('propietarios/<int:pk>/editar/', views.editar_propietario, name='editar_propietario'),
    path('propietarios/<int:pk>/eliminar/', views.eliminar_propietario, name='eliminar_propietario'),

    # Pacientes (RF-06, RF-08)
    path('', views.lista_pacientes, name='lista_pacientes'),
    path('nuevo/', views.crear_paciente, name='crear_paciente'),
    path('<int:pk>/', views.ficha_paciente, name='ficha_paciente'),
    path('<int:pk>/editar/', views.editar_paciente, name='editar_paciente'),
    path('<int:pk>/eliminar/', views.eliminar_paciente, name='eliminar_paciente'),

    # Vacunas
    path('<int:paciente_id>/vacunas/nueva/', views.crear_vacuna, name='crear_vacuna'),
    path('vacunas/<int:pk>/editar/', views.editar_vacuna, name='editar_vacuna'),
    path('vacunas/<int:pk>/eliminar/', views.eliminar_vacuna, name='eliminar_vacuna'),
]
