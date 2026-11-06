from django.urls import path

from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),

    # Citas (RF-09 a RF-13)
    path('', views.lista_citas, name='lista_citas'),
    path('calendario/', views.calendario_citas, name='calendario_citas'),
    path('nueva/', views.crear_cita, name='crear_cita'),
    path('<int:pk>/', views.detalle_cita, name='detalle_cita'),
    path('<int:pk>/editar/', views.editar_cita, name='editar_cita'),
    path('<int:pk>/estado/', views.cambiar_estado_cita, name='cambiar_estado_cita'),
    path('<int:pk>/eliminar/', views.eliminar_cita, name='eliminar_cita'),
    path('disponibilidad/', views.disponibilidad, name='disponibilidad_citas'),

    # Veterinarios
    path('veterinarios/', views.lista_veterinarios, name='lista_veterinarios'),
    path('veterinarios/nuevo/', views.crear_veterinario, name='crear_veterinario'),
    path('veterinarios/<int:pk>/editar/', views.editar_veterinario, name='editar_veterinario'),
]
