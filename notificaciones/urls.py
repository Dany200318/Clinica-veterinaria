from django.urls import path

from . import views

urlpatterns = [
    path('configuracion/', views.configuracion_correo, name='configuracion_correo'),
    path('historial/', views.historial_notificaciones, name='historial_notificaciones'),
    path('enviar-recordatorios/', views.ejecutar_recordatorios, name='ejecutar_recordatorios'),
    path('reenviar/<int:pk>/', views.reenviar_notificacion, name='reenviar_notificacion'),
]
