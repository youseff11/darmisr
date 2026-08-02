from decimal import Decimal

from .models import Book


class Cart:
    SESSION_KEY = "store_cart"
    COUPON_KEY = "store_coupon_code"

    def __init__(self, request):
        self.session = request.session
        self.data = self.session.get(self.SESSION_KEY, {})

    @staticmethod
    def item_key(book_id, book_format):
        return f"{book_id}:{book_format}"

    def add(self, book, book_format="physical", quantity=1, override=False):
        if book_format not in {"physical", "digital"}:
            raise ValueError("صيغة الكتاب غير صحيحة.")
        if not book.available_for(book_format):
            raise ValueError("هذه النسخة غير متاحة حاليًا.")

        quantity = max(1, int(quantity))
        if book_format == "digital":
            quantity = 1
        else:
            quantity = min(quantity, book.physical_stock)

        key = self.item_key(book.pk, book_format)
        if key not in self.data:
            self.data[key] = {
                "book_id": book.pk,
                "format": book_format,
                "quantity": 0,
            }

        if override:
            self.data[key]["quantity"] = quantity
        else:
            new_quantity = self.data[key]["quantity"] + quantity
            if book_format == "digital":
                new_quantity = 1
            else:
                new_quantity = min(new_quantity, book.physical_stock)
            self.data[key]["quantity"] = new_quantity
        self.save()

    def remove(self, key):
        if key in self.data:
            del self.data[key]
            self.save()

    def clear(self):
        self.session.pop(self.SESSION_KEY, None)
        self.session.pop(self.COUPON_KEY, None)
        self.session.modified = True
        self.data = {}

    def save(self):
        self.session[self.SESSION_KEY] = self.data
        self.session.modified = True

    def set_coupon(self, code):
        self.session[self.COUPON_KEY] = code
        self.session.modified = True

    def remove_coupon(self):
        self.session.pop(self.COUPON_KEY, None)
        self.session.modified = True

    @property
    def coupon_code(self):
        return self.session.get(self.COUPON_KEY, "")

    def __len__(self):
        return sum(item["quantity"] for item in self.data.values())

    def __iter__(self):
        book_ids = {item["book_id"] for item in self.data.values()}
        books = Book.objects.filter(id__in=book_ids, is_active=True).prefetch_related("authors")
        book_map = {book.pk: book for book in books}

        missing_keys = []
        for key, stored in list(self.data.items()):
            book = book_map.get(stored["book_id"])
            if not book or not book.available_for(stored["format"]):
                missing_keys.append(key)
                continue
            quantity = int(stored["quantity"])
            if stored["format"] == "digital":
                quantity = 1
            else:
                quantity = min(quantity, book.physical_stock)
            price = book.price_for(stored["format"]) or Decimal("0.00")
            yield {
                "key": key,
                "book": book,
                "format": stored["format"],
                "format_label": "نسخة إلكترونية" if stored["format"] == "digital" else "نسخة ورقية",
                "quantity": quantity,
                "price": price,
                "line_total": (price * quantity).quantize(Decimal("0.01")),
            }

        if missing_keys:
            for key in missing_keys:
                self.data.pop(key, None)
            self.save()

    @property
    def subtotal(self):
        return sum((item["line_total"] for item in self), Decimal("0.00"))

    @property
    def has_physical_items(self):
        return any(item["format"] == "physical" for item in self)

    def contains(self, book_id, book_format=None):
        if book_format:
            return self.item_key(book_id, book_format) in self.data
        return any(item["book_id"] == book_id for item in self.data.values())
