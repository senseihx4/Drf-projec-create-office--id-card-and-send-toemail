from django.urls import path
from . import views

urlpatterns = [
    path("checkout/<int:membership_type>/", views.create_checkout, name="create_checkout"),
    path("success/", views.payment_success, name="payment_success"),
    path("cancel/", views.payment_cancel, name="payment_cancel"),
]
