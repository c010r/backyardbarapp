from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.orders_home, name='home'),
    path('registro/', views.register_view, name='register'),
    path('verificar/', views.verify_view, name='verify'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('menu/', views.menu_view, name='menu'),
    path('pedido/<int:order_id>/', views.order_status_view, name='order_status'),
    path('api/pedido/<int:order_id>/estado/', views.order_status_api, name='order_status_api'),
    path('api/pedido/crear/', views.place_order, name='place_order'),
    path('panel/pedidos/', views.panel_orders, name='panel_orders'),
    path('panel/pedidos/<int:order_id>/', views.panel_order_detail, name='panel_order_detail'),
    path('panel/pedidos/<int:order_id>/estado/', views.panel_update_status, name='panel_update_status'),
]
