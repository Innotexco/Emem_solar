from django.urls import path
from . import views

app_name = "account"

urlpatterns = [
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('profile/', views.update_profile, name='profile'),
    path('upload-verification/', views.upload_verification_images, name='upload_verification_images'),
    path('verification-pending/', views.verification_pending, name='verification_pending'),
    path('delete-image/<int:image_id>/', views.delete_verification_image, name='delete_verification_image'),
    path('pending_verifications/', views.pending_verifications, name='pending_verifications'),
    path('verify_profile/<int:profile_id>/', views.verify_profile, name='verify_profile'),

    path('forgot-password/',             views.forgot_password,       name='forgot_password'),
    path('forgot-password/sent/',                     views.forgot_password_sent,  name='forgot_password_sent'),
    path('reset-password/<uidb64>/<token>/',          views.reset_password,        name='reset_password'),
    path('reset-password/done/',                      views.reset_password_done,   name='reset_password_done'),
]
