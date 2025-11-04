from django import forms
from .models import Sale
from geopy.geocoders import GoogleV3
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)

class SaleForm(forms.ModelForm):
    address = forms.CharField(max_length=255, required=True, help_text="Start typing an address and select from suggestions.")
    latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    longitude = forms.FloatField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Sale
        fields = [
            'job_number', 'name', 'address', 'latitude', 'longitude', 'sale_date',
            'products_sold', 'amount', 'notes', 'commission', 'phone_number',
            'sale_amount_split', 'accountability_amount'
        ]
        widgets = {
            'sale_date': forms.DateInput(attrs={'type': 'date'}),
            'products_sold': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'phone_number': forms.TextInput(attrs={'placeholder': 'e.g., +1-123-456-7890'}),
            'accountability_amount': forms.TextInput(attrs={'readonly': 'readonly'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        address = cleaned_data.get('address')
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        if not name:
            raise forms.ValidationError("Name is required.")
        if not address:
            raise forms.ValidationError("Please select a valid address using the autocomplete field.")
        if not latitude or not longitude:
            # Fallback to server-side geocoding
            geolocator = GoogleV3(api_key='AIzaSyA7A4meMvKdqnjXpZ0WKzJB-P6oUtIlvgs')
            try:
                logger.info(f"Attempting server-side geocoding for address: {address}")
                location = geolocator.geocode(address, timeout=10)
                if location:
                    cleaned_data['latitude'] = location.latitude
                    cleaned_data['longitude'] = location.longitude
                    logger.info(f"Server-side geocoded: ({location.latitude}, {location.longitude})")
                else:
                    logger.warning(f"Server-side geocoding failed for address: {address}")
                    raise forms.ValidationError("Could not geocode the address. Please ensure it is valid.")
            except (GeocoderTimedOut, GeocoderServiceError) as e:
                logger.error(f"Server-side geocoding error for {address}: {str(e)}")
                raise forms.ValidationError(f"Geocoding error: {str(e)}")
        return cleaned_data

    def save(self, commit=True, user=None):
        instance = super().save(commit=False)
        if user:
            instance.user = user
        instance.latitude = self.cleaned_data.get('latitude')
        instance.longitude = self.cleaned_data.get('longitude')
        instance.save()
        return instance

class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, help_text='Required.')
    last_name = forms.CharField(max_length=30, required=True, help_text='Required.')
    email = forms.EmailField(max_length=254, required=True, help_text='Required. Enter a valid email address.')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with that username (case-insensitive) already exists.")
        if len(username) > 50:
            raise forms.ValidationError("Username cannot exceed 50 characters.")
        return username.lower()

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['username'].lower()
        if commit:
            user.save()
        return user

class UserProfileForm(forms.ModelForm):
    new_password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput,
        required=False,
        help_text="Enter a new password if you want to change it."
    )
    new_password2 = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput,
        required=False,
        help_text="Confirm your new password."
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exclude(id=self.instance.id).exists():
            raise forms.ValidationError("This email address is already in use by another user.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')

        if new_password1 and new_password2 and new_password1 != new_password2:
            raise forms.ValidationError("The new passwords do not match.")
        if new_password1 and len(new_password1) < 8:
            raise forms.ValidationError("The new password must be at least 8 characters long.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password1 = self.cleaned_data.get('new_password1')
        if new_password1:
            user.set_password(new_password1)
        if commit:
            user.save()
        return user