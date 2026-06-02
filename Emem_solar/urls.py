from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.contrib.auth import views as auth_views
from django.conf.urls.static import static

urlpatterns = [
    path('', include("main.urls")),
    path('account/', include("account.urls")),
    path('admin/', admin.site.urls),
    
    
    path("__reload__/", include("django_browser_reload.urls")),
    # ^ this path can be almost anything — __reload__ is conventional
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

