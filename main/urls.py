from django.urls import path, include
from . import views
 
app_name = "main"


urlpatterns = [
    path("", views.home, name="home"),
    path("products/", views.products, name="products"),
    path("products/inverter/", views.inverter_products, name="inverter_products"),
    # Residental HI SL Series
    path("products/inverter/hi-3-6k-sl/", views.residential_HI_3_6k_SL, name="residential_HI_3_6k_SL"),
    path("products/inverter/hi-8k-sl/", views.residential_HI_8k_SL, name="residential_HI_8k_SL"),
    path("products/inverter/hi-12k-sl/", views.residential_HI_12k_SL, name="residential_HI_12k_SL"),
    
    # Residential HI TL Series
    path("products/inverter/hi-12k-tl/", views.residential_HI_12k_TL, name="residential_HI_12k_TL"),
    path("products/inverter/hi-15k-tl/", views.residential_HI_15k_TL, name="residential_HI_15k_TL"),
    path("products/inverter/hi-20k-tl/", views.residential_HI_20k_TL, name="residential_HI_20k_TL"),
    
    # Residential HI OFF-GRID Series
    path("products/inverter/hi-4k-sl/", views.residential_HI_4k_SL, name="residential_HI_4k_SL"),
    path("products/inverter/hi-6k-sl/", views.residential_HI_6k_SL, name="residential_HI_6k_SL"),
    path("products/inverter/hi-8k-sl-og/", views.residential_HI_8k_SL_OG, name="residential_HI_8k_SL_OG"),
    path("products/inverter/hi-10k-sl/", views.residential_HI_10k_SL, name="residential_HI_10k_SL"),
    
    # Commercial HI TH Series
    path("products/inverter/hi-15-25k-th/", views.commercial_HI_15_25k_TH, name="commercial_HI_15_25k_TH"),
    path("products/inverter/hi-29-60k-th/", views.commercial_HI_29_60k_TH, name="commercial_HI_29_60k_TH"),
    path("products/inverter/hi-80-125k-th/", views.commercial_HI_80_125k_TH, name="commercial_HI_80_125k_TH"),

    path("products/battery/", views.battery_products, name="battery_products"),
    path("products/battery/lithium-8kwh/", views.lithium_battery_8kwh, name="lithium_battery_8kwh"),
    path("products/battery/lithium-16kwh/", views.lithium_battery_16kwh, name="lithium_battery_16kwh"),
    path("products/battery/lithium-17-5kwh/", views.lithium_battery_17_5kwh, name="lithium_battery_17_5kwh"),
    
    
    path("products/panel/", views.solarPanels_products, name="panel_products"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    
    # Cart
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
