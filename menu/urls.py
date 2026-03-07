from django.urls import path
from . import views

app_name = 'menu'

urlpatterns = [
    # ── Menú público ──────────────────────────
    path('', views.menu_view, name='menu_home'),
    path('menu/<int:table_number>/', views.menu_view, name='menu_table'),
    path('categoria/<int:category_id>/', views.menu_category, name='menu_category'),
    path('menu/<int:table_number>/categoria/<int:category_id>/', views.menu_category, name='menu_table_category'),

    # ── Auth ──────────────────────────────────
    path('panel/login/', views.panel_login, name='panel_login'),
    path('panel/logout/', views.panel_logout, name='panel_logout'),

    # ── Panel ─────────────────────────────────
    path('panel/', views.panel_dashboard, name='panel_dashboard'),

    # Categorías
    path('panel/categorias/', views.panel_categories, name='panel_categories'),
    path('panel/categorias/nueva/', views.panel_category_form, name='panel_category_create'),
    path('panel/categorias/<int:pk>/editar/', views.panel_category_form, name='panel_category_edit'),
    path('panel/categorias/<int:pk>/eliminar/', views.panel_category_delete, name='panel_category_delete'),

    # Items
    path('panel/items/', views.panel_items, name='panel_items'),
    path('panel/items/nuevo/', views.panel_item_form, name='panel_item_create'),
    path('panel/items/<int:pk>/editar/', views.panel_item_form, name='panel_item_edit'),
    path('panel/items/<int:pk>/eliminar/', views.panel_item_delete, name='panel_item_delete'),

    # Mesas y QR
    path('panel/mesas/', views.panel_tables, name='panel_tables'),
    path('panel/mesas/nueva/', views.panel_table_form, name='panel_table_create'),
    path('panel/mesas/<int:pk>/editar/', views.panel_table_form, name='panel_table_edit'),
    path('panel/mesas/<int:pk>/eliminar/', views.panel_table_delete, name='panel_table_delete'),
    path('panel/mesas/<int:pk>/generar-qr/', views.panel_generate_qr, name='panel_generate_qr'),

    # Configuración
    path('panel/configuracion/', views.panel_config, name='panel_config'),
]
