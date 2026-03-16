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

    # Comandas
    path('panel/comandas/', views.panel_orders, name='panel_orders'),
    path('panel/comandas/json/', views.panel_orders_json, name='panel_orders_json'),
    path('panel/comandas/<int:pk>/estado/', views.panel_order_status, name='panel_order_status'),

    # Pedidos — Cliente
    path('menu/<int:table_number>/pedir/', views.place_order, name='place_order'),
    path('pedido/<int:order_id>/estado/', views.order_status, name='order_status'),

    # Barra — POS
    path('panel/barra/', views.bar_pos, name='bar_pos'),
    path('panel/barra/cobrar/', views.bar_checkout, name='bar_checkout'),
    path('panel/barra/ticket/<int:pk>/', views.bar_ticket, name='bar_ticket'),
    path('panel/barra/ticket/<int:pk>/entregar/', views.bar_deliver, name='bar_deliver'),
    path('panel/barra/historial/', views.bar_history, name='bar_history'),
]
