from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from app import views

urlpatterns = [
    path("", views.home, name="home"),
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("funcionalidades/", views.painel_funcionalidades, name="funcionalidades"),
    path("catalogo/", views.catalogo_alimentos, name="catalogo"),
    path("aditivos/", views.painel_aditivos, name="aditivos"),
    path("consistencias/", views.consistencias, name="consistencias"),
    path("trocas/", views.sugestoes_troca, name="trocas"),
    path("historico/", views.historico_simulacoes, name="historico"),
    path("comparar/", views.comparar_alimentos, name="comparar"),
    path("simulacao/", views.simulacao_refeicao, name="simulacao"),
    path("simulacao/remover/<int:item_id>/", views.remover_item, name="remover_item"),
    path("laudo/", views.laudo_simulacao, name="laudo"),
    path("relatorio/html/", views.exportar_relatorio, name="exportar_relatorio"),
]