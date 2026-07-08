from django.contrib import admin
from django.urls import include, path
from restaurants.views import health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health-check'),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("restaurants.urls")),
]
