from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Sale(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    job_number = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    street = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=10)
    sale_date = models.DateField(default=timezone.now)
    products_sold = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    commission = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    sale_amount_split = models.PositiveIntegerField(default=1)
    accountability_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.job_number} - {self.name}"