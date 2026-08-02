from django.db import OperationalError, ProgrammingError

from .cart import Cart
from .models import Category, SiteSettings, Wishlist


def store_context(request):
    try:
        site_settings = SiteSettings.load()
        navigation_categories = Category.objects.filter(is_active=True)[:10]
    except (OperationalError, ProgrammingError):
        site_settings = SiteSettings()
        navigation_categories = []

    wishlist_count = 0
    if request.user.is_authenticated:
        try:
            wishlist_count = Wishlist.objects.filter(user=request.user).count()
        except (OperationalError, ProgrammingError):
            wishlist_count = 0

    cart = Cart(request)
    return {
        "site_settings": site_settings,
        "navigation_categories": navigation_categories,
        "cart_count": len(cart),
        "wishlist_count": wishlist_count,
    }
