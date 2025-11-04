from django.urls import path
from django.shortcuts import redirect
from django.contrib.auth import logout
from . import views
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView

def redirect_to_sales(request):
    return redirect('sale_list')

def custom_logout(request):
    logout(request)
    return redirect('login')

urlpatterns = [
    path('', redirect_to_sales, name='home'),  # Redirect root URL to /sales/
    path('login/', LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', custom_logout, name='logout'),  # Use custom logout view
    path('signup/', views.signup, name='signup'),
    path('password_reset/', PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html', success_url='/login/'), name='password_reset_confirm'),
    path('reset/done/', PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
    path('sales/', views.sale_list, name='sale_list'),
    path('sales/load-more/', views.sale_list_load_more, name='sale_list_load_more'),
    path('sales/new/', views.sale_new, name='sale_new'),
    path('sales/<int:pk>/edit/', views.sale_edit, name='sale_edit'),
    path('sales/<int:pk>/delete/', views.sale_delete, name='sale_delete'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('manage_sales/', views.manage_sales, name='manage_sales'),
]