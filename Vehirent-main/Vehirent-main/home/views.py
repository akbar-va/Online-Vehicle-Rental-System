from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import *
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q
from datetime import datetime
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponse
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.units import inch
# Create your views here.
def index(request):
    return render(request, 'index.html')


def customer_register(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            return render(request, "register.html", {"error": "Passwords do not match"})

        if User.objects.filter(username=email).exists():
            return render(request, "register.html", {"error": "Email already registered"})

        user = User.objects.create_user(username=email, email=email, password=password)
        user.first_name = name
        user.save()

        Customer.objects.create(user=user, phone=phone)
        messages.success(request, "Registration successful! Please log in.")
        return redirect("customer_login")

    return render(request, "register.html")

def customer_login(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            return redirect("customer_dashboard")  # Redirect to dashboard after login
        else:
            return render(request, "login.html", {"error": "Invalid email or password"})

    return render(request, "login.html")


def customer_logout(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("customer_login")

@login_required
def customer_dashboard(request):
    try:
        customer = request.user.customer  
    except Customer.DoesNotExist:
        messages.error(request, "You are not a registered customer.")
        return redirect("customer_register")

    rentals = Rental.objects.filter(customer=customer)
    vehicles = Vehicle.objects.all()
    payments = Payment.objects.filter(rental__customer=customer)
    

    context = {
        "rentals": rentals,
        "vehicles": vehicles,
        "payments": payments,
    }
    return render(request, "dashboard.html", context)

def admin_login(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')

    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_superuser:
            login(request, user)
            return redirect("admin_dashboard")
        else:
            return render(request, "admin_login.html", {"error": "Invalid credentials or not an admin."})

    return render(request, "admin_login.html")

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):


    current_date = timezone.now().date()
    
    available_vehicles = Vehicle.objects.exclude(
        rental__start_date__lte=current_date,
        rental__end_date__gte=current_date
    ).filter(available=True)
    
    customers = Customer.objects.all()
    vehicles = Vehicle.objects.all()
    rentals = Rental.objects.all()
    payments = Payment.objects.all()
    
    total_payment = sum(payment.amount_paid for payment in payments)
    
    context = {
        "customers": customers,
        "vehicles": vehicles,
        "available_vehicles": available_vehicles,
        "rented_vehicles_count": vehicles.count() - available_vehicles.count(),  # Pre-calculate this
        "rentals": rentals,
        "payments": payments,
        "total_payment": total_payment,
    }
    return render(request, "admin_dashboard.html", context)

def admin_logout(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("admin_login")

def add_vehicle(request):
    if request.method == "POST":
        name = request.POST.get("name")
        brand = request.POST.get("brand")
        model_year = request.POST.get("model_year")
        price_per_day = request.POST.get("price_per_day")
        description = request.POST.get("description")
        available = request.POST.get("available") == "on"  # Checkbox handling
        image = request.FILES.get("image")  # Handle image upload

        # Save the vehicle to the database
        Vehicle.objects.create(
            name=name,
            brand=brand,
            model_year=model_year,
            price_per_day=price_per_day,
            description=description,
            available=available,
            image=image,
        )
        return redirect("admin_dashboard")  # Redirect to dashboard after adding

    return render(request, "add_vehicle.html")

def list_vehicles(request):
    vehicles = Vehicle.objects.all()  # Fetch all vehicles
    return render(request, "list_vehicles.html", {"vehicles": vehicles})

def view_vehicle(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    booked_dates = Rental.objects.filter(vehicle=vehicle).values_list('start_date', 'end_date')
    # Convert date ranges into a list of individual dates
    booked_days = []
    for start_date, end_date in booked_dates:
        current_date = start_date
        while current_date <= end_date:
            booked_days.append(current_date)
            current_date += timedelta(days=1)

    booked_days = [day.strftime('%Y-%m-%d') for day in booked_days]

    print(booked_days)
    return render(request, "view_vehicle.html", {"vehicle": vehicle, "booked_days": booked_days})

@login_required
def book_vehicle(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    customer = Customer.objects.get(user=request.user)

    if request.method == "POST":
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")

        # Convert string to date format
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect("view_vehicle", vehicle_id=vehicle.id)

        # Ensure the end date is after the start date
        if start_date >= end_date:
            messages.error(request, "End date must be after start date.")
            return redirect("view_vehicle", vehicle_id=vehicle.id)

        # Check vehicle availability
        if not Rental.is_vehicle_available(vehicle, start_date, end_date):
            messages.error(request, "This vehicle is not available for the selected dates.")
            return redirect("view_vehicle", vehicle_id=vehicle.id)

        # Calculate total price
        days = (end_date - start_date).days
        total_price = days * vehicle.price_per_day

        # Create Rental record
        rental = Rental.objects.create(
            customer=customer,
            vehicle=vehicle,
            start_date=start_date,
            end_date=end_date,
            total_price=total_price,
            is_fully_paid=True,  # Mark as fully paid
        )

        # Create Payment record with the full amount
        Payment.objects.create(
            rental=rental,
            amount_paid=total_price,
        )

        messages.success(request, f"Vehicle booked successfully! Total price: ₹{total_price}.")
        return redirect("customer_dashboard")

    return redirect("view_vehicle", vehicle_id=vehicle.id)


def complete_payment(request, rental_id):
    rental = get_object_or_404(Rental, id=rental_id, customer=request.user.customer)

    if rental.is_fully_paid:
        messages.info(request, "This rental is already fully paid.")
        return redirect("customer_dashboard")

 
    
    Payment.objects.create(rental=rental, amount_paid=rental.total_price)
    rental.is_fully_paid = True

    if request.method == "POST":
        rental.is_fully_paid = True
        rental.vehicle.is_available = False  # Mark vehicle as unavailable
        rental.vehicle.save()
        rental.save()
        messages.success(request, "Payment completed successfully!")
        return redirect("customer_dashboard")


    messages.success(request, f"Payment of ₹{rental.total_price} completed successfully!")
    return redirect("customer_dashboard")

@login_required
def download_receipt(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id, rental__customer=request.user.customer)
    
    # Create a PDF response
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    
    # Set up styles and colors
    primary_color = HexColor("#2c3e50")  # Dark blue
    accent_color = HexColor("#e74c3c")  # Red
    light_gray = HexColor("#f5f5f5")
    
    # Page dimensions
    width, height = letter
    
    # Add header with logo and company info
    pdf.setFillColor(primary_color)
    pdf.rect(0, height - 100, width, 100, fill=True, stroke=False)
    
    pdf.setFillColor(white)
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawString(100, height - 60, "VehicleRent")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(100, height - 85, "Pallipuram, Cherthala, Kerala, India")
    pdf.drawString(100, height - 100, "Phone: 9393489493 | Email: info@vehiclerent.com")
    
    # Add receipt title
    pdf.setFillColor(primary_color)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(width/2, height - 150, "PAYMENT RECEIPT")
    
    # Add decorative line
    pdf.setStrokeColor(accent_color)
    pdf.setLineWidth(2)
    pdf.line(100, height - 160, width - 100, height - 160)
    
    # Customer information section
    pdf.setFillColor(black)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(100, height - 200, "CUSTOMER INFORMATION")
    
    pdf.setFont("Helvetica", 10)
    customer_info = [
        f"Receipt ID: {payment.id}",
        f"Customer Name: {payment.rental.customer.user.get_full_name()}",
        f"Customer Email: {payment.rental.customer.user.email}",
    ]
    
    for i, info in enumerate(customer_info):
        pdf.drawString(120, height - 220 - (i * 20), info)
    
    # Rental details section
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(100, height - 300, "RENTAL DETAILS")
    
    pdf.setFont("Helvetica", 10)
    rental_info = [
        f"Vehicle: {payment.rental.vehicle.name} ({payment.rental.vehicle.brand} {payment.rental.vehicle.model_year})",
        f"Rental Period: {payment.rental.start_date.strftime('%b %d, %Y')} to {payment.rental.end_date.strftime('%b %d, %Y')}",
        f"Rental Days: {(payment.rental.end_date - payment.rental.start_date).days} days",
    ]
    
    for i, info in enumerate(rental_info):
        pdf.drawString(120, height - 320 - (i * 20), info)
    
    # Payment details section with styled box
    pdf.setFillColor(light_gray)
    pdf.rect(100, height - 440, width - 200, 80, fill=True, stroke=False)
    
    pdf.setFillColor(primary_color)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(100, height - 420, "PAYMENT INFORMATION")
    
    pdf.setFillColor(black)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(120, height - 445, "Amount Paid:")
    pdf.drawString(350, height - 445, f"Rs.{payment.amount_paid:,.2f}")
    
    pdf.drawString(120, height - 465, "Payment Date:")
    pdf.drawString(350, height - 465, payment.payment_date.strftime('%b %d, %Y %I:%M %p'))
    
    
    # Add thank you message
    pdf.setFillColor(accent_color)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawCentredString(width/2, height - 530, "Thank you for your business!")
    
    pdf.setFillColor(black)
    pdf.setFont("Helvetica", 10)
    pdf.drawCentredString(width/2, height - 550, "Please keep this receipt for your records.")
    pdf.drawCentredString(width/2, height - 570, "For any questions, contact support@vehiclerent.com")
    
    # Add footer
    pdf.setFillColor(primary_color)
    pdf.rect(0, 40, width, 40, fill=True, stroke=False)
    
    pdf.setFillColor(white)
    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(width/2, 50, "VehicleRent - Professional Vehicle Rental Services")
    pdf.drawCentredString(width/2, 30, "© 2023 VehicleRent. All rights reserved.")
    
    # Finalize the PDF
    pdf.showPage()
    pdf.save()
    
    # Return the PDF as a response
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="VehicleRent_Receipt_{payment.id}.pdf"'
    return response

@login_required
def add_feedback(request, rental_id):
    rental = get_object_or_404(Rental, id=rental_id, customer=request.user.customer)
    
    if request.method == "POST":
        message = request.POST.get("message")
        if message:
            Feedback.objects.create(
                rental=rental,
                message=message
            )
            messages.success(request, "Your feedback has been submitted successfully!")
            return redirect("customer_dashboard")
        else:
            messages.error(request, "Please provide a message.")
    
    return render(request, "add_feedback.html", {"rental": rental})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def view_feedbacks(request):
    feedbacks = Feedback.objects.all().order_by('-created_at')
    return render(request, "view_feedbacks.html", {"feedbacks": feedbacks})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def reply_feedback(request, feedback_id):
    feedback = get_object_or_404(Feedback, id=feedback_id)
    
    if request.method == "POST":
        admin_reply = request.POST.get("admin_reply")
        if admin_reply:
            feedback.admin_reply = admin_reply
            feedback.is_admin_reply = True
            feedback.replied_at = timezone.now()
            feedback.save()
            messages.success(request, "Reply sent successfully!")
            return redirect("view_feedbacks")
        else:
            messages.error(request, "Please provide a reply.")
    
    return render(request, "reply_feedback.html", {"feedback": feedback})