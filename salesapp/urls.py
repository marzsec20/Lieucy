from django.urls import path, include
from core.admin import admin_site  # Import custom admin site

urlpatterns = [
    path('admin/', admin_site.urls),  # Use custom admin site
    path('', include('core.urls')),   # Include core app URLs
]