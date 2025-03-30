from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path("register/", views.customer_register, name="customer_register"),
    path("login/", views.customer_login, name="customer_login"),
    path("logout/", views.customer_logout, name="customer_logout"),
    path("dashboard/", views.customer_dashboard, name="customer_dashboard"),
    path("admin-login/", views.admin_login, name="admin_login"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin_logout/", views.admin_logout, name="admin_logout"),
    path("add-vehicle/", views.add_vehicle, name="add_vehicle"),
    path("vehicles/", views.list_vehicles, name="list_vehicles"),
    path("vehicles/<int:vehicle_id>/", views.view_vehicle, name="view_vehicle"),  
    path("vehicles/<int:vehicle_id>/book/", views.book_vehicle, name="book_vehicle"),
    path("complete-payment/<int:rental_id>/", views.complete_payment, name="complete_payment"),
    path('download_receipt/<int:payment_id>/', views.download_receipt, name='download_receipt'),
    path('add-feedback/<int:rental_id>/', views.add_feedback, name='add_feedback'),
    path('view-feedbacks/', views.view_feedbacks, name='view_feedbacks'),
    path('reply-feedback/<int:feedback_id>/', views.reply_feedback, name='reply_feedback'),
]