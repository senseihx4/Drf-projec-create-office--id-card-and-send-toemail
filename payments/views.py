import stripe
from django.conf import settings
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

stripe.api_key = settings.STRIPE_SECRET_KEY

MEMBERSHIP_PRICES = {
    1: 600,    # Fairy Time - $6/month
    2: 3000,   # Fairy Circle - $30/month
    3: 6000,   # Fairy World - $60/month
}

MEMBERSHIP_NAMES = {
    1: 'Fairy Time',
    2: 'Fairy Circle',
    3: 'Fairy World',
}

# Existing Stripe product IDs (None = create product on the fly)
MEMBERSHIP_PRODUCT_IDS = {
    1: 'prod_UAA5fUV1LJF1y2',  # Fairy Time
    2: 'prod_U9uLoeLAm1RSFG',  # Fairy Circle
    3: 'prod_UAA7Gbhl2YGXkZ',  # Fairy World
}


@login_required
def create_checkout(request, membership_type):
    amount = MEMBERSHIP_PRICES.get(membership_type)
    name = MEMBERSHIP_NAMES.get(membership_type)

    if not amount:
        messages.error(request, "Invalid membership type.")
        return redirect('plan')

    product_id = MEMBERSHIP_PRODUCT_IDS.get(membership_type)
    if product_id:
        price_data = {
            "currency": "usd",
            "product": product_id,
            "unit_amount": amount,
        }
    else:
        price_data = {
            "currency": "usd",
            "product_data": {"name": f"{name} Membership"},
            "unit_amount": amount,
        }

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price_data": price_data, "quantity": 1}],
        mode="payment",
        metadata={
            "user_id": request.user.id,
            "membership_type": membership_type,
        },
        success_url=request.build_absolute_uri('/payments/success/') + '?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=request.build_absolute_uri('/payments/cancel/'),
    )

    return redirect(checkout_session.url)


def payment_success(request):
    session_id = request.GET.get('session_id')

    if not session_id:
        messages.error(request, "Invalid session.")
        return redirect('plan')

    checkout_session = stripe.checkout.Session.retrieve(session_id)
    user_id = checkout_session.metadata.get('user_id')
    membership_type = checkout_session.metadata.get('membership_type')

    if user_id and membership_type:
        from login.models import User
        User.objects.filter(id=user_id).update(membership_type=int(membership_type))
        messages.success(request, f"Welcome! Your {MEMBERSHIP_NAMES.get(int(membership_type))} membership is now active.")
    else:
        messages.success(request, "Payment successful!")

    return redirect('home_page')


def payment_cancel(request):
    messages.error(request, "Payment cancelled.")
    return redirect('plan')
