from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction
from django.db.models import Avg, Count, F, Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator

from .cart import Cart
from .forms import (
    AuthorApplicationForm,
    CheckoutForm,
    ContactForm,
    CouponForm,
    NewsletterForm,
    ReviewForm,
    SignupForm,
)
from .models import (
    Author,
    BlogPost,
    Book,
    Category,
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


def _safe_next_url(request, fallback):
    candidate = request.POST.get("next") or request.GET.get("next")
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return fallback


def _wants_json(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _coupon_for_cart(cart):
    if not cart.coupon_code:
        return None
    try:
        return Coupon.objects.get(code__iexact=cart.coupon_code, is_active=True)
    except Coupon.DoesNotExist:
        cart.remove_coupon()
        return None


def calculate_cart_totals(cart):
    site_settings = SiteSettings.load()
    subtotal = cart.subtotal
    coupon = _coupon_for_cart(cart)
    discount = coupon.discount_amount(subtotal) if coupon else Decimal("0.00")
    discounted_subtotal = max(subtotal - discount, Decimal("0.00"))
    shipping = Decimal("0.00")
    if cart.has_physical_items and discounted_subtotal < site_settings.free_shipping_threshold:
        shipping = site_settings.default_shipping_cost
    total = discounted_subtotal + shipping
    return {
        "subtotal": subtotal,
        "coupon": coupon,
        "discount": discount,
        "shipping": shipping,
        "total": total.quantize(Decimal("0.01")),
        "free_shipping_remaining": max(
            site_settings.free_shipping_threshold - discounted_subtotal,
            Decimal("0.00"),
        ),
    }


def home(request):
    active_books = Book.objects.filter(is_active=True).select_related("category").prefetch_related("authors")
    categories = (
        Category.objects.filter(is_active=True)
        .annotate(book_count=Count("books", filter=Q(books__is_active=True)))
        .order_by("sort_order", "name")[:10]
    )
    context = {
        "categories": categories,
        "featured_books": active_books.filter(is_featured=True)[:8],
        "new_books": active_books.filter(is_new=True)[:8],
        "bestsellers": active_books.filter(is_bestseller=True).order_by("-sales_count")[:8],
        "discounted_books": active_books.filter(
            Q(physical_old_price__gt=F("physical_price"))
            | Q(digital_old_price__gt=F("digital_price"))
        )[:6],
        "featured_authors": Author.objects.filter(is_featured=True)[:5],
        "posts": BlogPost.objects.filter(is_published=True)[:3],
        "events": Event.objects.filter(is_active=True, starts_at__gte=timezone.now())[:3],
        "book_count": active_books.count(),
        "author_count": Author.objects.count(),
        "category_count": Category.objects.filter(is_active=True).count(),
        "newsletter_form": NewsletterForm(),
    }
    return render(request, "store/home.html", context)


def book_list(request):
    books = Book.objects.filter(is_active=True).select_related("category").prefetch_related("authors")
    q = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()
    author_slug = request.GET.get("author", "").strip()
    year = request.GET.get("year", "").strip()
    book_format = request.GET.get("format", "").strip()
    availability = request.GET.get("availability", "").strip()
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()
    sort = request.GET.get("sort", "newest")

    if q:
        books = books.filter(
            Q(title__icontains=q)
            | Q(subtitle__icontains=q)
            | Q(authors__name__icontains=q)
            | Q(isbn__icontains=q)
            | Q(short_description__icontains=q)
            | Q(description__icontains=q)
        )
    if category_slug:
        books = books.filter(category__slug=category_slug)
    if author_slug:
        books = books.filter(authors__slug=author_slug)
    if year.isdigit():
        books = books.filter(publication_year=int(year))
    if book_format == "physical":
        books = books.filter(physical_price__gt=0)
    elif book_format == "digital":
        books = books.filter(digital_price__gt=0)
    if availability == "in_stock":
        books = books.filter(physical_stock__gt=0)
    elif availability == "digital":
        books = books.filter(digital_price__gt=0)

    try:
        if min_price:
            value = Decimal(min_price)
            books = books.filter(Q(physical_price__gte=value) | Q(digital_price__gte=value))
        if max_price:
            value = Decimal(max_price)
            books = books.filter(Q(physical_price__lte=value) | Q(digital_price__lte=value))
    except (InvalidOperation, ValueError):
        messages.warning(request, "تعذر تطبيق نطاق السعر؛ يرجى إدخال أرقام صحيحة.")

    ordering = {
        "newest": "-created_at",
        "title": "title",
        "price_low": "physical_price",
        "price_high": "-physical_price",
        "rating": "-average_rating",
        "bestselling": "-sales_count",
    }
    books = books.order_by(ordering.get(sort, "-created_at")).distinct()
    total_results = books.count()
    paginator = Paginator(books, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
        "total_results": total_results,
        "categories": Category.objects.filter(is_active=True),
        "authors": Author.objects.filter(books__is_active=True).distinct(),
        "years": Book.objects.filter(is_active=True)
        .order_by("-publication_year")
        .values_list("publication_year", flat=True)
        .distinct(),
        "filters": {
            "q": q,
            "category": category_slug,
            "author": author_slug,
            "year": year,
            "format": book_format,
            "availability": availability,
            "min_price": min_price,
            "max_price": max_price,
            "sort": sort,
        },
    }
    return render(request, "store/book_list.html", context)


def book_detail(request, slug):
    book = get_object_or_404(
        Book.objects.select_related("category").prefetch_related("authors", "images"),
        slug=slug,
        is_active=True,
    )
    Book.objects.filter(pk=book.pk).update(views_count=F("views_count") + 1)
    selected_format = request.GET.get("format", book.default_format)
    if selected_format not in {"physical", "digital"} or not book.available_for(selected_format):
        selected_format = book.default_format

    reviews = book.reviews.filter(is_approved=True).select_related("user")
    user_review = None
    in_wishlist = False
    if request.user.is_authenticated:
        user_review = Review.objects.filter(user=request.user, book=book).first()
        in_wishlist = Wishlist.objects.filter(user=request.user, book=book).exists()

    related_books = (
        Book.objects.filter(category=book.category, is_active=True)
        .exclude(pk=book.pk)
        .select_related("category")
        .prefetch_related("authors")[:4]
    )
    context = {
        "book": book,
        "selected_format": selected_format,
        "selected_price": book.price_for(selected_format),
        "selected_old_price": book.old_price_for(selected_format),
        "selected_discount": book.discount_for(selected_format),
        "reviews": reviews,
        "user_review": user_review,
        "review_form": ReviewForm(instance=user_review),
        "in_wishlist": in_wishlist,
        "related_books": related_books,
    }
    return render(request, "store/book_detail.html", context)


def author_detail(request, slug):
    author = get_object_or_404(Author, slug=slug)
    books = author.books.filter(is_active=True).select_related("category").prefetch_related("authors")
    return render(request, "store/author_detail.html", {"author": author, "books": books})


@login_required
@require_POST
def add_review(request, slug):
    book = get_object_or_404(Book, slug=slug, is_active=True)
    current = Review.objects.filter(user=request.user, book=book).first()
    form = ReviewForm(request.POST, instance=current)
    if form.is_valid():
        review = form.save(commit=False)
        review.user = request.user
        review.book = book
        review.save()
        average = book.reviews.filter(is_approved=True).aggregate(value=Avg("rating"))["value"] or 0
        Book.objects.filter(pk=book.pk).update(average_rating=average)
        messages.success(request, "شكرًا لك، تم حفظ تقييمك.")
    else:
        messages.error(request, "تعذر حفظ التقييم. راجع البيانات وحاول مرة أخرى.")
    return redirect(f"{book.get_absolute_url()}#reviews")


def cart_detail(request):
    cart = Cart(request)
    items = list(cart)
    totals = calculate_cart_totals(cart)
    return render(
        request,
        "store/cart.html",
        {"cart_items": items, "coupon_form": CouponForm(), **totals},
    )


@require_POST
def cart_add(request, book_id):
    book = get_object_or_404(Book, pk=book_id, is_active=True)
    book_format = request.POST.get("format", book.default_format)
    try:
        quantity = int(request.POST.get("quantity", 1))
        Cart(request).add(book, book_format=book_format, quantity=quantity)
        message = f"تمت إضافة «{book.title}» إلى السلة."
        messages.success(request, message)
        if _wants_json(request):
            return JsonResponse({"ok": True, "message": message, "cart_count": len(Cart(request))})
    except (ValueError, TypeError) as exc:
        message = str(exc) or "تعذر إضافة الكتاب إلى السلة."
        messages.error(request, message)
        if _wants_json(request):
            return JsonResponse({"ok": False, "message": message}, status=400)
    return redirect(_safe_next_url(request, book.get_absolute_url()))


@require_POST
def cart_update(request, key):
    cart = Cart(request)
    try:
        book_id, book_format = key.split(":", 1)
        book = get_object_or_404(Book, pk=int(book_id), is_active=True)
        quantity = int(request.POST.get("quantity", 1))
        if quantity <= 0:
            cart.remove(key)
        else:
            cart.add(book, book_format=book_format, quantity=quantity, override=True)
        messages.success(request, "تم تحديث السلة.")
    except (ValueError, TypeError):
        messages.error(request, "تعذر تحديث هذا العنصر.")
    return redirect("store:cart")


@require_POST
def cart_remove(request, key):
    Cart(request).remove(key)
    messages.info(request, "تم حذف العنصر من السلة.")
    return redirect("store:cart")


@require_POST
def apply_coupon(request):
    cart = Cart(request)
    form = CouponForm(request.POST)
    if form.is_valid():
        coupon = Coupon.objects.filter(code__iexact=form.cleaned_data["code"]).first()
        if coupon and coupon.is_valid(cart.subtotal):
            cart.set_coupon(coupon.code)
            messages.success(request, f"تم تطبيق الكوبون {coupon.code}.")
        else:
            messages.error(request, "الكوبون غير صالح أو لا يحقق الحد الأدنى للطلب.")
    return redirect("store:cart")


@require_POST
def remove_coupon(request):
    Cart(request).remove_coupon()
    messages.info(request, "تم إلغاء كود الخصم.")
    return redirect("store:cart")


def checkout(request):
    cart = Cart(request)
    items = list(cart)
    if not items:
        messages.info(request, "السلة فارغة. أضف كتابًا قبل إتمام الطلب.")
        return redirect("store:book_list")

    totals = calculate_cart_totals(cart)
    if request.method == "POST":
        form = CheckoutForm(request.POST, user=request.user, cart=cart)
        if form.is_valid():
            try:
                with transaction.atomic():
                    locked_books = {
                        book.pk: book
                        for book in Book.objects.select_for_update().filter(
                            pk__in=[item["book"].pk for item in items]
                        )
                    }
                    for item in items:
                        current_book = locked_books[item["book"].pk]
                        if not current_book.available_for(item["format"]):
                            raise ValueError(f"النسخة المطلوبة من «{current_book.title}» لم تعد متاحة.")
                        if item["format"] == "physical" and item["quantity"] > current_book.physical_stock:
                            raise ValueError(f"الكمية المتاحة من «{current_book.title}» أقل من المطلوبة.")

                    order = form.save(commit=False)
                    order.user = request.user if request.user.is_authenticated else None
                    order.subtotal = totals["subtotal"]
                    order.discount = totals["discount"]
                    order.shipping_cost = totals["shipping"]
                    order.total = totals["total"]
                    order.coupon = totals["coupon"]
                    order.coupon_code = totals["coupon"].code if totals["coupon"] else ""
                    order.payment_status = (
                        Order.PaymentStatus.UNPAID
                        if order.payment_method == Order.PaymentMethod.COD
                        else Order.PaymentStatus.PENDING
                    )
                    order.save()

                    for item in items:
                        current_book = locked_books[item["book"].pk]
                        OrderItem.objects.create(
                            order=order,
                            book=current_book,
                            title=current_book.title,
                            isbn=current_book.isbn,
                            book_format=item["format"],
                            unit_price=item["price"],
                            quantity=item["quantity"],
                            line_total=item["line_total"],
                        )
                        updates = {"sales_count": F("sales_count") + item["quantity"]}
                        if item["format"] == "physical":
                            updates["physical_stock"] = F("physical_stock") - item["quantity"]
                        Book.objects.filter(pk=current_book.pk).update(**updates)

                    if totals["coupon"]:
                        Coupon.objects.filter(pk=totals["coupon"].pk).update(
                            used_count=F("used_count") + 1
                        )
                    cart.clear()
                    request.session["last_order_number"] = order.order_number
                messages.success(request, "تم استلام طلبك بنجاح.")
                return redirect("store:order_success", order_number=order.order_number)
            except ValueError as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "يرجى مراجعة بيانات الشحن والدفع.")
    else:
        form = CheckoutForm(user=request.user, cart=cart)

    return render(
        request,
        "store/checkout.html",
        {"form": form, "cart_items": items, **totals},
    )


def order_success(request, order_number):
    order = get_object_or_404(Order.objects.prefetch_related("items"), order_number=order_number)
    allowed = request.session.get("last_order_number") == order_number
    if request.user.is_authenticated:
        allowed = allowed or order.user_id == request.user.id or request.user.is_staff
    if not allowed:
        raise Http404
    return render(request, "store/order_success.html", {"order": order})


@login_required
def my_orders(request):
    orders = request.user.orders.prefetch_related("items").all()
    return render(request, "store/my_orders.html", {"orders": orders})


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order.objects.prefetch_related("items__book"), order_number=order_number)
    if order.user_id != request.user.id and not request.user.is_staff:
        raise Http404
    return render(request, "store/order_detail.html", {"order": order})


@login_required
def download_book(request, item_id):
    item = get_object_or_404(
        OrderItem.objects.select_related("order", "book"),
        pk=item_id,
        book_format="digital",
        order__user=request.user,
    )
    if item.order.payment_status != Order.PaymentStatus.PAID and item.order.status != Order.Status.COMPLETED:
        messages.warning(request, "يصبح التنزيل متاحًا بعد تأكيد الدفع.")
        return redirect("store:order_detail", order_number=item.order.order_number)
    if not item.book or not item.book.digital_file:
        raise Http404("الملف غير متاح.")
    return FileResponse(
        item.book.digital_file.open("rb"),
        as_attachment=True,
        filename=item.book.digital_file.name.rsplit("/", 1)[-1],
    )


@login_required
def wishlist(request):
    items = Wishlist.objects.filter(user=request.user).select_related("book__category").prefetch_related(
        "book__authors"
    )
    return render(request, "store/wishlist.html", {"wishlist_items": items})


@login_required
@require_POST
def wishlist_toggle(request, book_id):
    book = get_object_or_404(Book, pk=book_id, is_active=True)
    item, created = Wishlist.objects.get_or_create(user=request.user, book=book)
    if created:
        message = "تمت إضافة الكتاب إلى المفضلة."
        active = True
    else:
        item.delete()
        message = "تم حذف الكتاب من المفضلة."
        active = False
    messages.success(request, message)
    if _wants_json(request):
        return JsonResponse({"ok": True, "active": active, "message": message})
    return redirect(_safe_next_url(request, book.get_absolute_url()))


def signup(request):
    if request.user.is_authenticated:
        return redirect("store:home")
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "مرحبًا بك، تم إنشاء حسابك بنجاح.")
            return redirect(_safe_next_url(request, reverse("store:home")))
    else:
        form = SignupForm()
    return render(
        request,
        "registration/register.html",
        {"form": form, "next": request.POST.get("next") or request.GET.get("next", "")},
    )


def login_view(request):
    if request.user.is_authenticated:
        return redirect("store:home")
    form = AuthenticationForm(request, data=request.POST or None)
    for field in form.fields.values():
        field.widget.attrs["class"] = "form-control"
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        messages.success(request, "تم تسجيل الدخول.")
        return redirect(_safe_next_url(request, reverse("store:home")))
    return render(
        request,
        "registration/login.html",
        {"form": form, "next": request.POST.get("next") or request.GET.get("next", "")},
    )


def about(request):
    return render(request, "store/about.html")


def faq(request):
    faqs = FAQ.objects.filter(is_active=True)
    sections = {}
    for item in faqs:
        sections.setdefault(item.section, []).append(item)
    return render(request, "store/faq.html", {"faq_sections": sections})


def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "وصلت رسالتك، وسيتواصل معك فريقنا قريبًا.")
            return redirect("store:contact")
    else:
        form = ContactForm()
    return render(request, "store/contact.html", {"form": form})


def author_application(request):
    if request.method == "POST":
        form = AuthorApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "تم إرسال مشروعك إلى لجنة النشر بنجاح.")
            return redirect("store:author_application")
    else:
        form = AuthorApplicationForm()
    return render(request, "store/author_application.html", {"form": form})


def academic_collaboration(request):
    return render(request, "store/academic_collaboration.html")


def blog_list(request):
    posts = BlogPost.objects.filter(is_published=True)
    selected_category = request.GET.get("category", "").strip()
    categories = list(
        BlogPost.objects.filter(is_published=True)
        .order_by("category")
        .values_list("category", flat=True)
        .distinct()
    )
    if selected_category:
        posts = posts.filter(category=selected_category)
    paginator = Paginator(posts, 9)
    return render(
        request,
        "store/blog_list.html",
        {
            "page_obj": paginator.get_page(request.GET.get("page")),
            "categories": categories,
            "selected_category": selected_category,
        },
    )


def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, is_published=True)
    related = BlogPost.objects.filter(is_published=True, category=post.category).exclude(pk=post.pk)[:3]
    return render(request, "store/blog_detail.html", {"post": post, "related_posts": related})


def event_list(request):
    events = Event.objects.filter(is_active=True)
    return render(request, "store/event_list.html", {"events": events})


def event_detail(request, slug):
    event = get_object_or_404(Event, slug=slug, is_active=True)
    return render(request, "store/event_detail.html", {"event": event})


@require_POST
def newsletter_subscribe(request):
    form = NewsletterForm(request.POST)
    if form.is_valid():
        subscriber, created = NewsletterSubscriber.objects.get_or_create(
            email=form.cleaned_data["email"], defaults={"is_active": True}
        )
        if not created and not subscriber.is_active:
            subscriber.is_active = True
            subscriber.save(update_fields=["is_active"])
        messages.success(request, "تم اشتراكك في النشرة البريدية.")
    else:
        messages.error(request, "أدخل بريدًا إلكترونيًا صحيحًا.")
    return redirect(_safe_next_url(request, reverse("store:home")))


def policy_page(request, slug):
    policies = {
        "privacy": (
            "سياسة الخصوصية",
            "نجمع فقط البيانات اللازمة لإنشاء الحساب وتنفيذ الطلب والتواصل بشأنه وتحسين تجربة الموقع. لا نبيع بيانات العملاء لأي طرف.\n\nقد نستعين بمقدمي خدمات موثوقين للشحن أو الدفع أو الاستضافة في حدود ما يلزم لتقديم الخدمة، مع التزامهم بحماية البيانات. يمكنك طلب تصحيح بياناتك أو إغلاق حسابك عبر صفحة التواصل.",
        ),
        "terms": (
            "شروط الاستخدام",
            "يلتزم المستخدم بتقديم بيانات صحيحة، وعدم إساءة استخدام الموقع أو محاولة الوصول غير المصرح به إلى الحسابات أو الملفات. الأسعار والتوافر قابلة للتحديث قبل تأكيد الطلب.\n\nكل محتوى الموقع محمي بحقوق الملكية الفكرية، ويُسمح باستخدامه الشخصي فقط. تحتفظ الدار بحق تعليق الحسابات المخالفة أو إلغاء الطلبات الناتجة عن خطأ تقني واضح مع رد أي مبالغ مستحقة.",
        ),
        "purchase": (
            "سياسة الشراء والاسترجاع",
            "يمكن طلب استبدال النسخة الورقية عند وصولها تالفة أو مختلفة عن الطلب، بشرط الإبلاغ خلال 48 ساعة مع صور توضح الحالة. تخضع طلبات الإرجاع الأخرى لمراجعة حالة الكتاب وتكاليف الشحن.\n\nلا تُسترد قيمة النسخة الرقمية بعد إتاحة رابط التنزيل، إلا عند وجود خلل تقني يمنع الوصول ولم يتمكن الفريق من معالجته. يبدأ تجهيز الطلب بعد تأكيده، وتختلف مدة التسليم حسب المحافظة وشركة الشحن.",
        ),
        "shipping": (
            "سياسة الشحن",
            "نشحن إلى المحافظات والمناطق التي تغطيها شركات التوصيل المتعاقد معها. تظهر تكلفة الشحن في ملخص السلة قبل تأكيد الطلب، وقد يحصل الطلب على شحن مجاني عند تجاوز الحد المحدد.\n\nيتلقى العميل تحديثًا عند انتقال الطلب إلى الشحن. يجب التأكد من صحة الهاتف والعنوان، وقد تؤدي محاولات التسليم المتكررة أو تغيير العنوان بعد الشحن إلى رسوم إضافية.",
        ),
        "intellectual-property": (
            "الملكية الفكرية",
            "جميع الكتب والأغلفة والنصوص والصور والملفات الرقمية محمية بحقوق المؤلف والنشر. يمنح شراء النسخة الإلكترونية ترخيصًا شخصيًا للقراءة ولا يجيز النسخ أو المشاركة أو إعادة البيع أو الإتاحة العامة.\n\nأي استخدام تجاري أو اقتباس موسع أو طلب حقوق ترجمة أو إعادة نشر يتطلب موافقة كتابية مسبقة من الدار وصاحب الحق.",
        ),
        "publishing": (
            "شروط النشر للمؤلفين",
            "يجب أن يكون مقدم المشروع مالكًا لحقوقه أو مفوضًا بإرساله، وأن يصرح بأي مواد مقتبسة أو حقوق لطرف ثالث. يخضع العمل لتقييم تحريري وقانوني، ولا يعني الإرسال قبول النشر أو التزامًا زمنيًا.\n\nعند القبول المبدئي، تُناقش خطة التحرير والإنتاج والتوزيع والحقوق في عقد مستقل وواضح. لا تُرسل المخطوطات الأصلية الوحيدة، ويُفضل الاحتفاظ بنسخة احتياطية من جميع الملفات.",
        ),
    }
    if slug not in policies:
        raise Http404
    title, content = policies[slug]
    return render(request, "store/policy_page.html", {"title": title, "content": content})


def search_suggestions(request):
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"results": []})
    books = (
        Book.objects.filter(is_active=True)
        .filter(Q(title__icontains=q) | Q(authors__name__icontains=q) | Q(isbn__icontains=q))
        .prefetch_related("authors")
        .distinct()[:6]
    )
    return JsonResponse(
        {
            "results": [
                {
                    "title": book.title,
                    "author": "، ".join(author.name for author in book.authors.all()),
                    "url": book.get_absolute_url(),
                    "price": f"{book.starting_price:.2f}",
                    "cover": book.cover.url if book.cover else "",
                }
                for book in books
            ]
        }
    )
