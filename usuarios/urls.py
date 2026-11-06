from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required
from django.urls import path

from . import views
from .forms import LoginForm

urlpatterns = [
    # Autenticación (RF-01)
    path('login/', login_not_required(auth_views.LoginView.as_view(
        template_name='usuarios/login.html',
        authentication_form=LoginForm,
        redirect_authenticated_user=True,
    )), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('mi-cuenta/password/', views.CambiarMiPasswordView.as_view(), name='cambiar_mi_password'),

    # Gestión de usuarios y roles (RF-02, RF-03) — solo administrador
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('usuarios/nuevo/', views.crear_usuario, name='crear_usuario'),
    path('usuarios/<int:pk>/editar/', views.editar_usuario, name='editar_usuario'),
    path('usuarios/<int:pk>/estado/', views.cambiar_estado_usuario, name='cambiar_estado_usuario'),
    path('usuarios/<int:pk>/password/', views.restablecer_password, name='restablecer_password'),
]
