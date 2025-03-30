from django.contrib.auth.models import User
from django.db import models
from decimal import Decimal
from django.utils import timezone

class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, unique=True)

    def __str__(self):
        return self.user.username

class Vehicle(models.Model):
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=100)
    model_year = models.IntegerField()
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="vehicle_images/", blank=True, null=True)
    available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.brand} {self.name} ({self.model_year})"


class Rental(models.Model):
    id = models.AutoField(primary_key=True)  # Ensure primary key is auto-incrementing
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_fully_paid = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Ensure no overlapping rentals for the same vehicle
        overlapping_rentals = Rental.objects.filter(
            vehicle=self.vehicle,
            start_date__lt=self.end_date,
            end_date__gt=self.start_date,
        ).exclude(id=self.id)  # Exclude the current rental if updating
        if overlapping_rentals.exists():
            raise ValueError("This vehicle is already booked for the selected dates.")
        super().save(*args, **kwargs)



    @staticmethod
    def is_vehicle_available(vehicle, start_date, end_date):
        """Check if the vehicle is available for the given date range."""
        overlapping_rentals = Rental.objects.filter(
            vehicle=vehicle,
            start_date__lt=end_date,
            end_date__gt=start_date,
        )
        return not overlapping_rentals.exists()

    def __str__(self):
        return f"{self.customer.user.username} - {self.vehicle.name} ({self.start_date} to {self.end_date})"

class Payment(models.Model):
    rental = models.OneToOneField(Rental, on_delete=models.CASCADE)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)

    
    def __str__(self):
        return f"Payment for {self.rental.vehicle.name} by {self.rental.customer.user.username}"

class Feedback(models.Model):
    rental = models.ForeignKey(Rental, on_delete=models.CASCADE, related_name='feedbacks')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_admin_reply = models.BooleanField(default=False)
    admin_reply = models.TextField(blank=True, null=True)
    replied_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Feedback for {self.rental.vehicle.name} by {self.rental.customer.user.username}"
