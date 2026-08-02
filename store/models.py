import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


def unique_slug(instance, value):
    """Generate a readable Unicode slug and keep it unique per model."""
    base = slugify(value, allow_unicode=True) or uuid.uuid4().hex[:8]
    candidate = base
    counter = 2
    queryset = instance.__class__.objects.all()
    if instance.pk:
        queryset = queryset.exclude(pk=instance.pk)
    while queryset.filter(slug=candidate).exists():
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


class SiteSettings(models.Model):
    site_name = models.CharField("اسم الدار", max_length=120, default="دار مصر للنشر")
    tagline = models.CharField("الشعار", max_length=180, default="نصنع معرفة تبقى")
    short_description = models.TextField(
        "وصف مختصر",
        default="دار نشر عربية تقدم كتبًا ورقية وإلكترونية مختارة بعناية.",
    )
    phone = models.CharField("الهاتف", max_length=40, blank=True)
    whatsapp = models.CharField("واتساب", max_length=40, blank=True)
    email = models.EmailField("البريد الإلكتروني", blank=True)
    address = models.CharField("العنوان", max_length=255, blank=True)
    facebook_url = models.URLField("فيسبوك", blank=True)
    instagram_url = models.URLField("إنستجرام", blank=True)
    free_shipping_threshold = models.DecimalField(
        "حد الشحن المجاني", max_digits=10, decimal_places=2, default=Decimal("1500.00")
    )
    default_shipping_cost = models.DecimalField(
        "تكلفة الشحن الافتراضية", max_digits=10, decimal_places=2, default=Decimal("75.00")
    )
    announcement = models.CharField(
        "شريط الإعلان", max_length=255, blank=True, default="شحن لجميع محافظات مصر"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "إعدادات الموقع"
        verbose_name_plural = "إعدادات الموقع"

    def __str__(self):
        return self.site_name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Category(models.Model):
    name = models.CharField("الاسم", max_length=100)
    name_en = models.CharField("الاسم بالإنجليزية", max_length=100, blank=True)
    slug = models.SlugField(max_length=140, unique=True, allow_unicode=True, blank=True)
    description = models.TextField("الوصف", blank=True)
    icon = models.CharField("أيقونة Bootstrap", max_length=60, default="bi-book")
    sort_order = models.PositiveIntegerField("الترتيب", default=0)
    is_active = models.BooleanField("ظاهر", default=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "تصنيف"
        verbose_name_plural = "التصنيفات"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return f"{reverse('store:book_list')}?category={self.slug}"


class Author(models.Model):
    name = models.CharField("اسم المؤلف", max_length=160)
    slug = models.SlugField(max_length=190, unique=True, allow_unicode=True, blank=True)
    bio = models.TextField("نبذة", blank=True)
    photo = models.ImageField("الصورة", upload_to="authors/", blank=True, null=True)
    nationality = models.CharField("الجنسية", max_length=100, blank=True)
    website = models.URLField("الموقع", blank=True)
    is_featured = models.BooleanField("مؤلف مميز", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "مؤلف"
        verbose_name_plural = "المؤلفون"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("store:author_detail", args=[self.slug])


class Book(models.Model):
    class Binding(models.TextChoices):
        HARDCOVER = "hardcover", "غلاف مقوى"
        PAPERBACK = "paperback", "غلاف ورقي"
        LEATHER = "leather", "تجليد فاخر"

    title = models.CharField("عنوان الكتاب", max_length=280)
    subtitle = models.CharField("العنوان الفرعي", max_length=280, blank=True)
    slug = models.SlugField(max_length=320, unique=True, allow_unicode=True, blank=True)
    authors = models.ManyToManyField(Author, related_name="books", verbose_name="المؤلفون")
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="books",
        verbose_name="التصنيف",
    )
    isbn = models.CharField("ISBN", max_length=32, unique=True)
    short_description = models.CharField("وصف مختصر", max_length=420, blank=True)
    description = models.TextField("الوصف", blank=True)
    publication_year = models.PositiveSmallIntegerField("سنة النشر", default=timezone.now().year)
    pages = models.PositiveIntegerField("عدد الصفحات", default=0)
    edition = models.CharField("الطبعة", max_length=80, blank=True)
    dimensions = models.CharField("المقاس", max_length=60, blank=True, default="17 × 24 سم")
    binding = models.CharField(
        "نوع الغلاف", max_length=20, choices=Binding.choices, default=Binding.PAPERBACK
    )
    language = models.CharField("اللغة", max_length=60, default="العربية")
    cover = models.ImageField("الغلاف", upload_to="books/", blank=True, null=True)
    cover_alt = models.CharField("النص البديل للغلاف", max_length=280, blank=True)

    physical_price = models.DecimalField(
        "سعر النسخة الورقية", max_digits=10, decimal_places=2, blank=True, null=True
    )
    physical_old_price = models.DecimalField(
        "السعر الورقي قبل الخصم", max_digits=10, decimal_places=2, blank=True, null=True
    )
    physical_stock = models.PositiveIntegerField("مخزون النسخة الورقية", default=0)
    digital_price = models.DecimalField(
        "سعر النسخة الإلكترونية", max_digits=10, decimal_places=2, blank=True, null=True
    )
    digital_old_price = models.DecimalField(
        "السعر الإلكتروني قبل الخصم", max_digits=10, decimal_places=2, blank=True, null=True
    )
    digital_file = models.FileField("ملف الكتاب الإلكتروني", upload_to="digital/", blank=True)
    sample_file = models.FileField("ملف الفهرس أو العينة", upload_to="samples/", blank=True)
    sample_url = models.URLField("رابط الفهرس أو العينة", blank=True)

    is_featured = models.BooleanField("مميز", default=False)
    is_new = models.BooleanField("إصدار جديد", default=False)
    is_bestseller = models.BooleanField("الأكثر مبيعًا", default=False)
    is_active = models.BooleanField("متاح للعرض", default=True)
    sales_count = models.PositiveIntegerField("عدد المبيعات", default=0)
    views_count = models.PositiveIntegerField("عدد المشاهدات", default=0)
    average_rating = models.DecimalField(
        "متوسط التقييم", max_digits=3, decimal_places=2, default=Decimal("0.00")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["isbn"]),
            models.Index(fields=["is_active", "-created_at"]),
        ]
        verbose_name = "كتاب"
        verbose_name_plural = "الكتب"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.title)
        if not self.cover_alt:
            self.cover_alt = f"غلاف كتاب {self.title}"
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        physical = self.physical_price is not None and self.physical_price > 0
        digital = self.digital_price is not None and self.digital_price > 0
        if not physical and not digital:
            raise ValidationError("يجب تحديد سعر لنسخة ورقية أو إلكترونية واحدة على الأقل.")

    def get_absolute_url(self):
        return reverse("store:book_detail", args=[self.slug])

    @property
    def has_physical(self):
        return self.physical_price is not None and self.physical_price > 0

    @property
    def has_digital(self):
        return self.digital_price is not None and self.digital_price > 0

    @property
    def default_format(self):
        if self.has_physical and self.physical_stock > 0:
            return "physical"
        if self.has_digital:
            return "digital"
        return "physical"

    @property
    def starting_price(self):
        prices = [price for price in (self.physical_price, self.digital_price) if price]
        return min(prices) if prices else Decimal("0.00")

    def price_for(self, book_format):
        return self.digital_price if book_format == "digital" else self.physical_price

    def old_price_for(self, book_format):
        return self.digital_old_price if book_format == "digital" else self.physical_old_price

    def available_for(self, book_format):
        if book_format == "digital":
            return self.has_digital
        return self.has_physical and self.physical_stock > 0

    def discount_for(self, book_format):
        price = self.price_for(book_format)
        old_price = self.old_price_for(book_format)
        if not price or not old_price or old_price <= price:
            return 0
        return int(((old_price - price) / old_price) * 100)

    @property
    def max_discount(self):
        return max(self.discount_for("physical"), self.discount_for("digital"))


class BookImage(models.Model):
    book = models.ForeignKey(Book, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField("الصورة", upload_to="books/gallery/")
    alt_text = models.CharField("النص البديل", max_length=280, blank=True)
    sort_order = models.PositiveIntegerField("الترتيب", default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "صورة كتاب"
        verbose_name_plural = "صور الكتب"

    def __str__(self):
        return f"{self.book.title} - {self.sort_order}"


class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, related_name="reviews", on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(
        "التقييم", validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField("الرأي", max_length=1200)
    is_approved = models.BooleanField("معتمد", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "book"], name="unique_user_book_review")
        ]
        verbose_name = "تقييم"
        verbose_name_plural = "التقييمات"

    def __str__(self):
        return f"{self.user} - {self.book} ({self.rating})"


class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, related_name="wishlisted_by", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "book"], name="unique_wishlist_book")
        ]
        verbose_name = "مفضلة"
        verbose_name_plural = "المفضلة"


class Coupon(models.Model):
    class DiscountType(models.TextChoices):
        PERCENT = "percent", "نسبة مئوية"
        FIXED = "fixed", "قيمة ثابتة"

    code = models.CharField("الكود", max_length=40, unique=True)
    discount_type = models.CharField(
        "نوع الخصم", max_length=10, choices=DiscountType.choices, default=DiscountType.PERCENT
    )
    value = models.DecimalField("قيمة الخصم", max_digits=10, decimal_places=2)
    minimum_order = models.DecimalField(
        "الحد الأدنى للطلب", max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    maximum_discount = models.DecimalField(
        "أقصى خصم", max_digits=10, decimal_places=2, blank=True, null=True
    )
    valid_from = models.DateTimeField("صالح من", default=timezone.now)
    valid_to = models.DateTimeField("صالح حتى")
    usage_limit = models.PositiveIntegerField("حد الاستخدام", default=0, help_text="صفر يعني بلا حد")
    used_count = models.PositiveIntegerField("عدد مرات الاستخدام", default=0)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "كوبون"
        verbose_name_plural = "الكوبونات"

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def is_valid(self, subtotal=Decimal("0.00")):
        now = timezone.now()
        within_usage = self.usage_limit == 0 or self.used_count < self.usage_limit
        return (
            self.is_active
            and self.valid_from <= now <= self.valid_to
            and within_usage
            and subtotal >= self.minimum_order
        )

    def discount_amount(self, subtotal):
        subtotal = Decimal(subtotal)
        if not self.is_valid(subtotal):
            return Decimal("0.00")
        if self.discount_type == self.DiscountType.PERCENT:
            discount = subtotal * (self.value / Decimal("100"))
        else:
            discount = self.value
        if self.maximum_discount:
            discount = min(discount, self.maximum_discount)
        return min(discount, subtotal).quantize(Decimal("0.01"))


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "قيد المراجعة"
        CONFIRMED = "confirmed", "تم التأكيد"
        PROCESSING = "processing", "قيد التجهيز"
        SHIPPED = "shipped", "تم الشحن"
        DELIVERED = "delivered", "تم التسليم"
        COMPLETED = "completed", "مكتمل"
        CANCELLED = "cancelled", "ملغي"

    class PaymentMethod(models.TextChoices):
        COD = "cod", "الدفع عند الاستلام"
        BANK = "bank", "تحويل بنكي"
        WALLET = "wallet", "محفظة إلكترونية"

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "غير مدفوع"
        PENDING = "pending", "بانتظار التحقق"
        PAID = "paid", "مدفوع"
        FAILED = "failed", "فشل"
        REFUNDED = "refunded", "مسترد"

    order_number = models.CharField("رقم الطلب", max_length=24, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="orders",
        blank=True,
        null=True,
    )
    full_name = models.CharField("الاسم الكامل", max_length=160)
    email = models.EmailField("البريد الإلكتروني")
    phone = models.CharField("الهاتف", max_length=40)
    country = models.CharField("الدولة", max_length=100, default="مصر")
    governorate = models.CharField("المحافظة", max_length=120)
    city = models.CharField("المدينة", max_length=120)
    address_line = models.CharField("العنوان التفصيلي", max_length=300)
    postal_code = models.CharField("الرمز البريدي", max_length=20, blank=True)
    notes = models.TextField("ملاحظات", blank=True)
    payment_method = models.CharField(
        "طريقة الدفع", max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.COD
    )
    payment_status = models.CharField(
        "حالة الدفع", max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID
    )
    status = models.CharField(
        "حالة الطلب", max_length=20, choices=Status.choices, default=Status.PENDING
    )
    subtotal = models.DecimalField("المجموع الفرعي", max_digits=10, decimal_places=2)
    discount = models.DecimalField(
        "الخصم", max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    shipping_cost = models.DecimalField(
        "الشحن", max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    total = models.DecimalField("الإجمالي", max_digits=10, decimal_places=2)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, blank=True, null=True)
    coupon_code = models.CharField("كود الخصم المحفوظ", max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "طلب"
        verbose_name_plural = "الطلبات"

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"DM{timezone.now():%y%m%d}{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("store:order_detail", args=[self.order_number])


class OrderItem(models.Model):
    class Format(models.TextChoices):
        PHYSICAL = "physical", "نسخة ورقية"
        DIGITAL = "digital", "نسخة إلكترونية"

    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.SET_NULL, blank=True, null=True)
    title = models.CharField("عنوان الكتاب", max_length=280)
    isbn = models.CharField("ISBN", max_length=32, blank=True)
    book_format = models.CharField("الصيغة", max_length=12, choices=Format.choices)
    unit_price = models.DecimalField("سعر الوحدة", max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField("الكمية", default=1)
    line_total = models.DecimalField("الإجمالي", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "عنصر طلب"
        verbose_name_plural = "عناصر الطلب"

    def __str__(self):
        return f"{self.title} × {self.quantity}"

    def save(self, *args, **kwargs):
        self.line_total = self.unit_price * self.quantity
        super().save(*args, **kwargs)


class BlogPost(models.Model):
    title = models.CharField("العنوان", max_length=250)
    slug = models.SlugField(max_length=280, unique=True, allow_unicode=True, blank=True)
    excerpt = models.CharField("المقتطف", max_length=420)
    content = models.TextField("المحتوى")
    image = models.ImageField("الصورة", upload_to="blog/", blank=True, null=True)
    category = models.CharField("التصنيف", max_length=100, default="ثقافة وكتب")
    author_name = models.CharField("اسم الكاتب", max_length=160, default="فريق دار مصر")
    published_at = models.DateTimeField("تاريخ النشر", default=timezone.now)
    is_published = models.BooleanField("منشور", default=True)
    is_featured = models.BooleanField("مميز", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-published_at"]
        verbose_name = "مقال"
        verbose_name_plural = "المقالات"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("store:blog_detail", args=[self.slug])

    @property
    def reading_time(self):
        words = len(self.content.split())
        return max(1, round(words / 200))


class Event(models.Model):
    class EventType(models.TextChoices):
        FAIR = "fair", "معرض كتاب"
        SIGNING = "signing", "حفل توقيع"
        SEMINAR = "seminar", "ندوة"
        WORKSHOP = "workshop", "ورشة عمل"
        ONLINE = "online", "لقاء رقمي"

    title = models.CharField("العنوان", max_length=250)
    slug = models.SlugField(max_length=280, unique=True, allow_unicode=True, blank=True)
    short_description = models.CharField("وصف مختصر", max_length=420, blank=True)
    description = models.TextField("الوصف")
    event_type = models.CharField(
        "نوع الفعالية", max_length=20, choices=EventType.choices, default=EventType.SEMINAR
    )
    image = models.ImageField("الصورة", upload_to="events/", blank=True, null=True)
    venue = models.CharField("المكان", max_length=220)
    is_online = models.BooleanField("عبر الإنترنت", default=False)
    starts_at = models.DateTimeField("يبدأ في")
    ends_at = models.DateTimeField("ينتهي في", blank=True, null=True)
    registration_url = models.URLField("رابط التسجيل", blank=True)
    is_active = models.BooleanField("ظاهر", default=True)

    class Meta:
        ordering = ["starts_at"]
        verbose_name = "فعالية"
        verbose_name_plural = "الفعاليات"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("store:event_detail", args=[self.slug])


class FAQ(models.Model):
    question = models.CharField("السؤال", max_length=300)
    answer = models.TextField("الإجابة")
    section = models.CharField("القسم", max_length=100, default="عام")
    sort_order = models.PositiveIntegerField("الترتيب", default=0)
    is_active = models.BooleanField("ظاهر", default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "سؤال شائع"
        verbose_name_plural = "الأسئلة الشائعة"

    def __str__(self):
        return self.question


class ContactMessage(models.Model):
    name = models.CharField("الاسم", max_length=160)
    email = models.EmailField("البريد الإلكتروني")
    phone = models.CharField("الهاتف", max_length=40, blank=True)
    subject = models.CharField("الموضوع", max_length=220)
    message = models.TextField("الرسالة")
    is_read = models.BooleanField("تمت القراءة", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "رسالة تواصل"
        verbose_name_plural = "رسائل التواصل"

    def __str__(self):
        return f"{self.name} - {self.subject}"


class AuthorApplication(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "جديد"
        REVIEWING = "reviewing", "قيد المراجعة"
        ACCEPTED = "accepted", "مقبول"
        REJECTED = "rejected", "غير مناسب حاليًا"

    name = models.CharField("الاسم", max_length=160)
    email = models.EmailField("البريد الإلكتروني")
    phone = models.CharField("الهاتف", max_length=40)
    specialization = models.CharField("التخصص", max_length=180)
    project_title = models.CharField("عنوان المشروع", max_length=280)
    synopsis = models.TextField("نبذة عن المشروع")
    sample_url = models.URLField("رابط العينة", blank=True)
    sample_file = models.FileField("ملف العينة", upload_to="author-applications/", blank=True)
    status = models.CharField("الحالة", max_length=20, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "طلب نشر"
        verbose_name_plural = "طلبات النشر"

    def __str__(self):
        return f"{self.name} - {self.project_title}"


class NewsletterSubscriber(models.Model):
    email = models.EmailField("البريد الإلكتروني", unique=True)
    is_active = models.BooleanField("نشط", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "مشترك نشرة"
        verbose_name_plural = "مشتركو النشرة"

    def __str__(self):
        return self.email
