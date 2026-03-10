from django.urls import path
from . import views
 
app_name = "main"


urlpatterns = [
    path("", views.home, name="home"),
    path("products/", views.products, name="products"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path('cart/', views.view_cart, name='cart'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/', views.update_cart, name='update_cart'),
    path('cart/remove/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/count/', views.cart_count, name='cart_count'),
    # Order URLs
    path('order/<str:item_id>/', views.order_now, name='order_now'),
    path('checkout/', views.checkout, name='checkout'),
    path('get_user_price/', views.get_user_price, name='get_user_price'),
    path('checkout/<str:item_id>/', views.checkout, name='checkout_item'),
    path('order-confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'), 
    path('api/pickup-stations/', views.get_pickup_stations, name='get_pickup_stations'),
    # path('api/pickup-stations/states/', views.get_states_with_stations, name='get_states'),
    path('api/states-with-stations/', views.get_states_with_stations, name='api_states_with_stations'),

    path('dashboard', views.admin_dashboard, name='dashboard'),
    path('dashboard/', views.customer_dashboard_view, name='customer_dashboard'),
    path('customer-order/', views.my_orders_view, name='my_orders'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),

    
    # Pickup Stations
    path('stations/', views.manage_pickup_stations, name='manage_stations'),
    path('stations/add/', views.add_pickup_station, name='add_station'),
    path('stations/<int:station_id>/edit/', views.edit_pickup_station, name='edit_station'),
    path('stations/<int:station_id>/delete/', views.delete_pickup_station, name='delete_station'),
    path('stations/<int:station_id>/toggle/', views.toggle_station_status, name='toggle_station'),
    
    # Stock Alerts
    path('stock-alerts/', views.manage_stock_alerts, name='manage_stock_alerts'),
    path('stock-alerts/add/', views.add_stock_alert, name='add_stock_alert'),
    path('stock-alerts/<int:alert_id>/edit/', views.edit_stock_alert, name='edit_stock_alert'),
    path('stock-alerts/<int:alert_id>/delete/', views.delete_stock_alert, name='delete_stock_alert'),
    path('stock-alerts/<int:alert_id>/toggle/', views.toggle_alert_status, name='toggle_alert'),

    path('orders/', views.view_orders, name='view_orders'),
    path('orders/<int:order_id>/', views.order_detail_view, name='cus_order_detail'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('invoice/<str:invoice_id>/', views.invoice_detail_view, name='invoice_detail'),
]
