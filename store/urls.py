from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = "store"

urlpatterns = [
    path("", views.home, name="home"),
    path("books/", views.book_list, name="book_list"),
    path("books/<str:slug>/", views.book_detail, name="book_detail"),
    path("authors/<str:slug>/", views.author_detail, name="author_detail"),
    path("books/<str:slug>/review/", views.add_review, name="add_review"),
    path("search/suggestions/", views.search_suggestions, name="search_suggestions"),

    path("cart/", views.cart_detail, name="cart"),
    path("cart/add/<int:book_id>/", views.cart_add, name="cart_add"),
    path("cart/update/<str:key>/", views.cart_update, name="cart_update"),
    path("cart/remove/<str:key>/", views.cart_remove, name="cart_remove"),
    path("cart/coupon/apply/", views.apply_coupon, name="apply_coupon"),
    path("cart/coupon/remove/", views.remove_coupon, name="remove_coupon"),
    path("checkout/", views.checkout, name="checkout"),
    path("orders/success/<str:order_number>/", views.order_success, name="order_success"),
    path("account/orders/", views.my_orders, name="my_orders"),
    path("account/orders/<str:order_number>/", views.order_detail, name="order_detail"),
    path("account/download/<int:item_id>/", views.download_book, name="download_book"),

    path("wishlist/", views.wishlist, name="wishlist"),
    path("wishlist/toggle/<int:book_id>/", views.wishlist_toggle, name="wishlist_toggle"),
    path("account/register/", views.signup, name="register"),
    path("account/login/", views.login_view, name="login"),
    path(
        "account/logout/",
        auth_views.LogoutView.as_view(next_page=reverse_lazy("store:home")),
        name="logout",
    ),
    path(
        "account/password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.html",
            success_url=reverse_lazy("store:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "account/password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "account/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            success_url=reverse_lazy("store:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "account/reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),

    path("about/", views.about, name="about"),
    path("faq/", views.faq, name="faq"),
    path("contact/", views.contact, name="contact"),
    path("publish-with-us/", views.author_application, name="author_application"),
    path("academic-collaboration/", views.academic_collaboration, name="academic_collaboration"),
    path("blog/", views.blog_list, name="blog_list"),
    path("blog/<str:slug>/", views.blog_detail, name="blog_detail"),
    path("events/", views.event_list, name="event_list"),
    path("events/<str:slug>/", views.event_detail, name="event_detail"),
    path("newsletter/subscribe/", views.newsletter_subscribe, name="newsletter_subscribe"),
    path("policies/<str:slug>/", views.policy_page, name="policy_page"),
]