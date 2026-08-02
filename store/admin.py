from django.contrib import admin

from .models import (
    Author,
    AuthorApplication,
    BlogPost,
    Book,
    BookImage,
    Category,
    ContactMessage,
    Coupon,
    Event,
    FAQ,
    NewsletterSubscriber,
    Order,
    OrderItem,
    Review,
    SiteSettings,
    Wishlist,
)


class BookImageInline(admin.TabularInline):
    model = BookImage
    extra = 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "name_en", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")
    search_fields = ("name", "name_en")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("name", "nationality", "is_featured", "created_at")
    list_filter = ("is_featured", "nationality")
    search_fields = ("name", "bio")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "physical_price",
        "digital_price",
        "physical_stock",
        "is_featured",
        "is_active",
    )
    list_filter = (
        "is_active",
        "is_featured",
        "is_new",
        "is_bestseller",
        "category",
        "publication_year",
        "binding",
    )
    list_editable = ("physical_price", "physical_stock", "is_featured", "is_active")
    search_fields = ("title", "subtitle", "isbn", "authors__name")
    autocomplete_fields = ("authors", "category")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("views_count", "sales_count", "average_rating", "created_at", "updated_at")
    inlines = (BookImageInline,)
    fieldsets = (
        ("بيانات الكتاب", {"fields": ("title", "subtitle", "slug", "authors", "category", "isbn")}),
        ("الوصف", {"fields": ("short_description", "description")}),
        (
            "البيانات الببليوجرافية",
            {"fields": ("publication_year", "pages", "edition", "dimensions", "binding", "language")},
        ),
        ("الصور والعينة", {"fields": ("cover", "cover_alt", "sample_file", "sample_url")}),
        (
            "النسخة الورقية",
            {"fields": ("physical_price", "physical_old_price", "physical_stock")},
        ),
        (
            "النسخة الإلكترونية",
            {"fields": ("digital_price", "digital_old_price", "digital_file")},
        ),
        (
            "الظهور والإحصاءات",
            {
                "fields": (
                    "is_featured",
                    "is_new",
                    "is_bestseller",
                    "is_active",
                    "sales_count",
                    "views_count",
                    "average_rating",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("book", "user", "rating", "is_approved", "created_at")
    list_filter = ("rating", "is_approved", "created_at")
    list_editable = ("is_approved",)
    search_fields = ("book__title", "user__username", "comment")


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("user", "book", "created_at")
    search_fields = ("user__username", "book__title")


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_type", "value", "minimum_order", "used_count", "is_active", "valid_to")
    list_filter = ("discount_type", "is_active")
    list_editable = ("is_active",)
    search_fields = ("code",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("book", "title", "isbn", "book_format", "unit_price", "quantity", "line_total")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "full_name", "total", "payment_method", "payment_status", "status", "created_at")
    list_filter = ("status", "payment_status", "payment_method", "created_at")
    list_editable = ("payment_status", "status")
    search_fields = ("order_number", "full_name", "email", "phone")
    date_hierarchy = "created_at"
    readonly_fields = (
        "order_number",
        "user",
        "subtotal",
        "discount",
        "shipping_cost",
        "total",
        "coupon",
        "coupon_code",
        "created_at",
        "updated_at",
    )
    inlines = (OrderItemInline,)


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "author_name", "published_at", "is_published", "is_featured")
    list_filter = ("is_published", "is_featured", "category")
    search_fields = ("title", "excerpt", "content")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "venue", "starts_at", "is_active")
    list_filter = ("is_active", "starts_at")
    search_fields = ("title", "description", "venue")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "section", "sort_order", "is_active")
    list_filter = ("section", "is_active")
    list_editable = ("sort_order", "is_active")
    search_fields = ("question", "answer")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "subject", "email", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    list_editable = ("is_read",)
    search_fields = ("name", "email", "phone", "subject", "message")
    readonly_fields = ("name", "email", "phone", "subject", "message", "created_at")


@admin.register(AuthorApplication)
class AuthorApplicationAdmin(admin.ModelAdmin):
    list_display = ("name", "project_title", "specialization", "status", "created_at")
    list_filter = ("status", "specialization", "created_at")
    list_editable = ("status",)
    search_fields = ("name", "email", "project_title", "synopsis")
    readonly_fields = ("created_at",)


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    list_editable = ("is_active",)
    search_fields = ("email",)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("الهوية", {"fields": ("site_name", "tagline", "short_description", "announcement")}),
        ("التواصل", {"fields": ("phone", "whatsapp", "email", "address")}),
        ("الشبكات", {"fields": ("facebook_url", "instagram_url")}),
        ("الشحن", {"fields": ("free_shipping_threshold", "default_shipping_cost")}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
