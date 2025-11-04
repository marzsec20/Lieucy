from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Sale

# Custom AdminSite to change "View site" URL
class CustomAdminSite(admin.AdminSite):
    site_url = '/sales/'  # Explicitly set "View site" URL
    index_url = '/sales/'  # Optional: Set index URL for consistency

# Instantiate custom admin site
admin_site = CustomAdminSite(name='custom_admin')

# Custom SaleAdmin
class SaleAdmin(admin.ModelAdmin):
    list_display = ('job_number', 'name', 'city', 'state', 'zip_code', 'phone_number', 'sale_date', 'amount', 'commission')
    list_filter = ('city', 'state', 'sale_date')
    search_fields = ('job_number', 'name', 'city', 'street', 'zip_code', 'phone_number')

# Custom UserAdmin
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'email', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email')

# Register models with custom admin site
admin_site.register(Sale, SaleAdmin)
admin_site.register(User, CustomUserAdmin)

# Prevent default admin site interference
try:
    admin.site.unregister(User)
except admin.site.NotRegistered:
    pass