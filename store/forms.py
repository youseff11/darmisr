from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import (
    AuthorApplication,
    ContactMessage,
    NewsletterSubscriber,
    Order,
    Review,
)


class StyledFormMixin:
    """Apply consistent Bootstrap-friendly classes without third-party packages."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css_class = "form-check-input"
            elif isinstance(widget, forms.RadioSelect):
                css_class = "form-check-input"
            elif isinstance(widget, forms.Select):
                css_class = "form-select"
            else:
                css_class = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css_class}".strip()
            if field.required:
                widget.attrs.setdefault("required", True)


class SignupForm(StyledFormMixin, UserCreationForm):
    first_name = forms.CharField(label="الاسم", max_length=150)
    email = forms.EmailField(label="البريد الإلكتروني")

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("first_name", "email", "username", "password1", "password2")
        labels = {"username": "اسم المستخدم"}

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("يوجد حساب مسجل بهذا البريد الإلكتروني.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        if commit:
            user.save()
        return user


class ReviewForm(StyledFormMixin, forms.ModelForm):
    rating = forms.TypedChoiceField(
        label="التقييم",
        choices=[(5, "5 — ممتاز"), (4, "4 — جيد جدًا"), (3, "3 — جيد"), (2, "2 — مقبول"), (1, "1 — ضعيف")],
        coerce=int,
        widget=forms.Select,
    )

    class Meta:
        model = Review
        fields = ("rating", "comment")
        labels = {"comment": "اكتب رأيك"}
        widgets = {
            "comment": forms.Textarea(
                attrs={"rows": 4, "placeholder": "ما الذي أعجبك في هذا الكتاب؟"}
            )
        }


class CheckoutForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Order
        fields = (
            "full_name",
            "email",
            "phone",
            "country",
            "governorate",
            "city",
            "address_line",
            "postal_code",
            "payment_method",
            "notes",
        )
        widgets = {
            "address_line": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "علامة مميزة أو ملاحظات للشحن"}),
        }

    def __init__(self, *args, user=None, cart=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.cart = cart
        self.fields["payment_method"].widget = forms.RadioSelect()
        self.fields["payment_method"].widget.attrs["class"] = "payment-methods"
        if user and user.is_authenticated:
            self.fields["full_name"].initial = user.get_full_name() or user.username
            self.fields["email"].initial = user.email

    def clean_payment_method(self):
        payment_method = self.cleaned_data["payment_method"]
        if (
            self.cart
            and not self.cart.has_physical_items
            and payment_method == Order.PaymentMethod.COD
        ):
            raise forms.ValidationError(
                "الدفع عند الاستلام غير متاح للطلبات الرقمية فقط. اختر التحويل أو المحفظة."
            )
        return payment_method


class ContactForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ("name", "email", "phone", "subject", "message")
        widgets = {
            "message": forms.Textarea(attrs={"rows": 6, "placeholder": "كيف يمكننا مساعدتك؟"})
        }


class AuthorApplicationForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = AuthorApplication
        fields = (
            "name",
            "email",
            "phone",
            "specialization",
            "project_title",
            "synopsis",
            "sample_url",
            "sample_file",
        )
        widgets = {
            "synopsis": forms.Textarea(
                attrs={"rows": 7, "placeholder": "الفكرة، الجمهور المستهدف، وما يميز العمل"}
            )
        }
        help_texts = {
            "sample_url": "يمكنك إرسال رابط Google Drive أو أي رابط متاح للمراجعة.",
            "sample_file": "صيغة PDF أو DOCX، ويفضل ألا يتجاوز الملف 10 ميجابايت.",
        }

    def clean_sample_file(self):
        sample = self.cleaned_data.get("sample_file")
        if sample and sample.size > 10 * 1024 * 1024:
            raise forms.ValidationError("حجم ملف العينة يجب ألا يتجاوز 10 ميجابايت.")
        return sample


class NewsletterForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = NewsletterSubscriber
        fields = ("email",)
        widgets = {"email": forms.EmailInput(attrs={"placeholder": "بريدك الإلكتروني"})}

    def clean_email(self):
        return self.cleaned_data["email"].lower().strip()


class CouponForm(StyledFormMixin, forms.Form):
    code = forms.CharField(
        label="كود الخصم",
        max_length=40,
        widget=forms.TextInput(attrs={"placeholder": "مثال: READ10"}),
    )

    def clean_code(self):
        return self.cleaned_data["code"].strip().upper()
