from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from .forms import SaleForm, CustomUserCreationForm, UserProfileForm
from .models import Sale
from django.db.models import Q, Sum, Count
from django.db.models.functions import TruncMonth, TruncYear, Coalesce
from django.db.models import DecimalField
import re
from datetime import datetime
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.conf import settings  # Added for API key
import logging

logger = logging.getLogger(__name__)

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user, backend='core.auth_backends.CaseInsensitiveModelBackend')
                return redirect('sale_list')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

@login_required
def sale_list(request):

    request.session['from_manage_sales'] = False  # Reset flag

    city = request.GET.get('city', '').strip()
    zip_code = request.GET.get('zip_code', '').strip()
    sales = Sale.objects.filter(user=request.user).order_by('-sale_date')
    
    # Apply filters for the sales list
    filtered_sales = sales

    if city:
        #city = re.sub(r'\bst\b', 'Saint', city, flags=re.IGNORECASE)
        filtered_sales = filtered_sales.filter(Q(city__iexact=city) | Q(city__icontains=city))
    if zip_code:
        filtered_sales = filtered_sales.filter(zip_code__iexact=zip_code)
    
    paginator = Paginator(sales, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Map shows all sales with valid coordinates, regardless of filter
    map_sales = sales.exclude(latitude__isnull=True).exclude(longitude__isnull=True).order_by('-sale_date')
    
    logger.info(f"sale_list - Google Maps API Key: {settings.GOOGLE_MAPS_API_KEY}")
    context = {
        'sales': page_obj,
        'map_sales': map_sales,
        'page_obj': page_obj,
        'search_city': city,  # Pass city for map geocoding
        'search_zip_code': zip_code,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,  # Add API key
    }
    return render(request, 'core/sale_list.html', context)

@login_required
def sale_list_load_more(request):
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    city = request.GET.get('city', '').strip()
    zip_code = request.GET.get('zip_code', '').strip()
    page = int(request.GET.get('page', 2))
    
    sales = Sale.objects.filter(user=request.user).order_by('-sale_date')
    
    if city:
        city = re.sub(r'\bst\b', 'Saint', city, flags=re.IGNORECASE)
        sales = sales.filter(Q(city__iexact=city) | Q(city__icontains=city))
    if zip_code:
        sales = sales.filter(zip_code__iexact=zip_code)
    
    paginator = Paginator(sales, 20)
    page_obj = paginator.get_page(page)
    
    sales_html = ''
    for sale in page_obj:
        sales_html += f'''
        <li class="list-group-item">
            <strong>{sale.job_number}</strong> - {sale.name}
            <a href="/sales/{sale.pk}/edit/" class="btn btn-sm btn-warning">Edit</a>
            <a href="/sales/{sale.pk}/delete/" class="btn btn-sm btn-danger">Delete</a>
            <br>
            Sale Date: {sale.sale_date.strftime("%b %d, %Y")}<br>
            Address: {sale.street}, {sale.city}, {sale.state} {sale.zip_code}<br>
        '''
        if sale.phone_number:
            sales_html += f'Phone: {sale.phone_number}<br>'
        sales_html += f'''
            Amount: ${sale.amount}'''
        if sale.commission:
            sales_html += f' | Commission: ${sale.commission}'
        sales_html += f'''<br>
            Products: {sale.products_sold or "N/A"}<br>
            Notes: {sale.notes or ""}<br>
        </li>
        '''
    
    has_next = page_obj.has_next()
    next_page = page_obj.next_page_number() if has_next else None
    
    return JsonResponse({
        'sales_html': sales_html,
        'has_next': has_next,
        'next_page': next_page
    })

@login_required
def sale_new(request):
    
    redirect_url = 'manage_sales' if request.session.get('from_manage_sales', False) else 'sale_list'  # MOVED Redirect HERE!!
    
    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            sale = form.save(commit=False, user=request.user)
            address = form.cleaned_data['address']
            # Parse address components
            parts = [part.strip() for part in address.split(',')]
            if len(parts) >= 4:
                sale.street = parts[0]
                sale.city = parts[-3]
                sale.state = parts[-2].split()[0]
                sale.zip_code = parts[-2].split()[-1] if len(parts[-2].split()) > 1 else ''
            else:
                sale.street = parts[0] if parts else ''
                sale.city = parts[1] if len(parts) > 1 else ''
                sale.state = parts[2].split()[0] if len(parts) > 2 else ''
                sale.zip_code = parts[2].split()[-1] if len(parts) > 2 and len(parts[2].split()) > 1 else ''
            # Set address for display
            sale.address = address
            # Get latitude/longitude from form
            sale.latitude = form.cleaned_data.get('latitude')
            sale.longitude = form.cleaned_data.get('longitude')
            amount = form.cleaned_data['amount']
            sale_amount_split = form.cleaned_data['sale_amount_split']
            sale.accountability_amount = amount / sale_amount_split if sale_amount_split > 0 else amount
            sale.save()

            return redirect(redirect_url)
                    
        logger.info(f"sale_new - Google Maps API Key: {settings.GOOGLE_MAPS_API_KEY}")
        
        # If form is invalid, re-render with redirect_url ***ADDED *** 
        return render(request, 'core/sale_form.html', {'form': form, 'redirect_url': redirect_url, 'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY})
    else:
        form = SaleForm(initial={'sale_amount_split': 1})

    logger.info(f"sale_new - Google Maps API Key: {settings.GOOGLE_MAPS_API_KEY}")

    return render(request, 'core/sale_form.html', {'form': form, 'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY})

@login_required
def sale_edit(request, pk):
    sale = Sale.objects.get(pk=pk, user=request.user)
    
    redirect_url = 'manage_sales' if request.session.get('from_manage_sales', False) else 'sale_list' # Moved Redirect HERE!
    
    if request.method == 'POST':
        form = SaleForm(request.POST, instance=sale)
        if form.is_valid():
            sale = form.save(commit=False, user=request.user)
            address = form.cleaned_data['address']
            # Parse address components
            parts = [part.strip() for part in address.split(',')]
            if len(parts) >= 4:
                sale.street = parts[0]
                sale.city = parts[-3]
                sale.state = parts[-2].split()[0]
                sale.zip_code = parts[-2].split()[-1] if len(parts[-2].split()) > 1 else ''
            else:
                sale.street = parts[0] if parts else ''
                sale.city = parts[1] if len(parts) > 1 else ''
                sale.state = parts[2].split()[0] if len(parts) > 2 else ''
                sale.zip_code = parts[2].split()[-1] if len(parts) > 2 and len(parts[2].split()) > 1 else ''
            # Set address for display
            sale.address = address
            # Get latitude/longitude from form
            sale.latitude = form.cleaned_data.get('latitude')
            sale.longitude = form.cleaned_data.get('longitude')
            amount = form.cleaned_data['amount']
            sale_amount_split = form.cleaned_data['sale_amount_split']
            sale.accountability_amount = amount / sale_amount_split if sale_amount_split > 0 else amount
            sale.save()
            
            return redirect(redirect_url)
            #return redirect('sale_list') ** Original Code **
        logger.info(f"sale_edit - Google Maps API Key: {settings.GOOGLE_MAPS_API_KEY}")
    else:
        form = SaleForm(
            instance=sale,
            initial={
                'address': f"{sale.street}, {sale.city}, {sale.state} {sale.zip_code}",
                'sale_amount_split': sale.sale_amount_split,
                'latitude': sale.latitude,
                'longitude': sale.longitude
            }
        )
    logger.info(f"sale_edit - Google Maps API Key: {settings.GOOGLE_MAPS_API_KEY}")
    return render(request, 'core/sale_form.html', {'form': form, 'redirect_url': redirect_url})
    #return render(request, 'core/sale_form.html', {'form': form}) ~~ CHANGED THIS TOO ^^

@login_required
def sale_delete(request, pk):
    sale = Sale.objects.get(pk=pk, user=request.user)
    redirect_url = 'manage_sales' if request.session.get('from_manage_sales', False) else 'sale_list' # MOVED Redirect Here !!
    if request.method == 'POST':
        sale.delete()
        
        return redirect(redirect_url)
        #return redirect('sale_list')  **Original Code**
    
    return render(request, 'core/sale_confirm_delete.html', {'sale': sale, 'redirect_url': redirect_url})
    #return render(request, 'core/sale_confirm_delete.html', {'sale': sale})  **Original Code**

@login_required
def profile_edit(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('sale_list')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'core/profile_edit.html', {'form': form})

@login_required
def dashboard(request):
    sales = Sale.objects.filter(user=request.user)
    
    total_career_sales = sales.aggregate(total=Coalesce(Sum('accountability_amount'), 0.0, output_field=DecimalField()))['total']
    
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    year = request.GET.get('year', '')
    city = request.GET.get('city', '').strip()
    
    filtered_sales = sales
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            filtered_sales = filtered_sales.filter(sale_date__gte=start_date)
        except ValueError:
            start_date = ''
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            filtered_sales = filtered_sales.filter(sale_date__lte=end_date)
        except ValueError:
            end_date = ''
    if city:
        city = re.sub(r'\bst\b', 'Saint', city, flags=re.IGNORECASE)
        filtered_sales = filtered_sales.filter(Q(city__iexact=city) | Q(city__icontains=city))
    
    # Filter out dates with no sales or zero accountability_amount
    sales_by_date = filtered_sales.filter(accountability_amount__gt=0).values('sale_date').annotate(
        total_amount=Coalesce(Sum('accountability_amount'), 0.0, output_field=DecimalField())
    ).order_by('sale_date')
    date_chart_data = {
        'labels': [item['sale_date'].strftime('%Y-%m-%d') for item in sales_by_date],
        'data': [float(item['total_amount']) for item in sales_by_date]
    }
    logger.info(f"Date Chart Data: {date_chart_data}")
    
    selected_year = year if year else timezone.now().year
    try:
        selected_year = int(selected_year)
    except ValueError:
        selected_year = timezone.now().year
    sales_by_month = filtered_sales.filter(sale_date__year=selected_year, accountability_amount__gt=0).annotate(
        month=TruncMonth('sale_date')
    ).values('month').annotate(
        count=Count('id'),
        total_amount=Coalesce(Sum('accountability_amount'), 0.0, output_field=DecimalField())
    ).order_by('month')
    month_chart_data = {
        'labels': [item['month'].strftime('%b %Y') for item in sales_by_month],
        'count_data': [item['count'] for item in sales_by_month],
        'amount_data': [float(item['total_amount']) for item in sales_by_month]
    }
    logger.info(f"Month Chart Data: {month_chart_data}")
    
    sales_by_city = filtered_sales.filter(accountability_amount__gt=0).values('city').annotate(
        total_amount=Coalesce(Sum('accountability_amount'), 0.0, output_field=DecimalField())
    ).order_by('-total_amount')
    city_chart_data = {
        'labels': [item['city'] for item in sales_by_city],
        'data': [float(item['total_amount']) for item in sales_by_city]
    }
    logger.info(f"City Chart Data: {city_chart_data}")
    
    years = sales.dates('sale_date', 'year', order='DESC').distinct()
    years = [year.year for year in years]
    
    context = {
        'total_career_sales': total_career_sales,
        'date_chart_data': date_chart_data,
        'month_chart_data': month_chart_data,
        'city_chart_data': city_chart_data,
        'years': years,
        'start_date': start_date,
        'end_date': end_date,
        'selected_year': selected_year,
        'city': city,
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def manage_sales(request):
    
    request.session['from_manage_sales'] = True  # Set flag
    
    search_query = request.GET.get('q', '').strip()
    sales = Sale.objects.filter(user=request.user).order_by('-sale_date')
    
    if search_query:
        sales = sales.filter(
            Q(job_number__icontains=search_query) |
            Q(name__icontains=search_query) |
            Q(street__icontains=search_query) |
            Q(city__icontains=search_query) |
            Q(state__icontains=search_query) |
            Q(zip_code__icontains=search_query) |
            Q(products_sold__icontains=search_query) |
            Q(notes__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )
    
    paginator = Paginator(sales, 20)  # 20 sales per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'sales': sales,  # For the table
        'page_obj': page_obj,  # For pagination
        'search_query': search_query,  # For the search input
    }
    return render(request, 'core/manage_sales.html', context)