from django import forms
from django.utils.translation import gettext_lazy as _
from .models import ContactMessage
import re

_NAME_RE = re.compile(r"^[A-Za-zА-Яа-яЁёІіЇїЄєҐґ'’\-\s]+$")

def _normalize_ws(value: str) -> str:
    # обрізаємо краї + стискаємо багато пробілів в один
    return re.sub(r"\s+", " ", (value or "").strip())

class ContactForm(forms.ModelForm):
    # honeypot (має бути порожнім)
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = ContactMessage
        fields = ["first_name", "last_name", "email", "phone", "subject", "message"]
        widgets = {
            "first_name": forms.TextInput(attrs={"placeholder": _("Іван")}),
            "last_name":  forms.TextInput(attrs={"placeholder": _("Петренко")}),
            "email":      forms.EmailInput(attrs={"placeholder": _("example@gmail.com")}),
            "phone":      forms.TextInput(attrs={"placeholder": _("Введіть номер телефону")}),
            "subject":    forms.TextInput(attrs={"placeholder": _("Введіть тему…")}),
            "message":    forms.Textarea(attrs={"placeholder": _("Введіть повідомлення…"), "rows": 5}),
        }
        labels = {
            "first_name": _("Ім'я"),
            "last_name":  _("Прізвище"),
            "email":      _("Електронна пошта"),
            "phone":      _("Номер телефону"),
            "subject":    _("Тема"),
            "message":    _("Ваше повідомлення"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # робимо обов'язковими ключові поля (на випадок, якщо в моделі вони optional)
        self.fields["first_name"].required = True
        self.fields["email"].required = True
        self.fields["subject"].required = True
        self.fields["message"].required = True
        # додаткове: м’яко обмежимо довжину вводу на рівні форми
        self.fields["subject"].max_length = 120
        self.fields["message"].max_length = 4000

    # ----- Поле honeypot
    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError(_("Виявлено спам."))
        return ""

    # ----- Ім'я
    def clean_first_name(self):
        value = _normalize_ws(self.cleaned_data.get("first_name"))
        if len(value) < 2:
            raise forms.ValidationError(_("Ім'я має містити щонайменше 2 символи."))
        if len(value) > 50:
            raise forms.ValidationError(_("Ім'я задовге (макс. 50 символів)."))
        if not _NAME_RE.match(value):
            raise forms.ValidationError(_("Ім'я може містити лише літери, пробіли, апостроф або дефіс."))
        return value

    # ----- Прізвище (необов'язкове)
    def clean_last_name(self):
        value = _normalize_ws(self.cleaned_data.get("last_name"))
        if not value:
            return ""
        if len(value) > 60:
            raise forms.ValidationError(_("Прізвище задовге (макс. 60 символів)."))
        if not _NAME_RE.match(value):
            raise forms.ValidationError(_("Прізвище може містити лише літери, пробіли, апостроф або дефіс."))
        return value

    # ----- Email
    def clean_email(self):
        value = (self.cleaned_data.get("email") or "").strip().lower()
        # EmailInput разом з EmailField у моделі зазвичай достатній,
        # але нормалізуємо регістр + базова перевірка
        if not value:
            raise forms.ValidationError(_("Вкажіть електронну пошту."))
        # простий safeguard: заборона прогалин усередині
        if " " in value:
            raise forms.ValidationError(_("Електронна пошта не може містити пробіли."))
        return value

    # ----- Телефон (необов'язковий, але якщо вказано — перевіряємо)
    def clean_phone(self):
        raw = (self.cleaned_data.get("phone") or "").strip()
        if not raw:
            return ""
        # лишаємо тільки цифри, плюс — для нормалізації
        digits = re.sub(r"\D", "", raw)
        # Перевіряємо довжину міжнародного формату
        if len(digits) < 10 or len(digits) > 15:
            raise forms.ValidationError(_("Невірний номер телефону. Вкажіть від 10 до 15 цифр."))
        normalized = "+" + digits
        return normalized

    # ----- Тема
    def clean_subject(self):
        value = _normalize_ws(self.cleaned_data.get("subject"))
        if len(value) < 3:
            raise forms.ValidationError(_("Тема надто коротка (мін. 3 символи)."))
        if len(value) > 120:
            raise forms.ValidationError(_("Тема задовга (макс. 120 символів)."))
        # Базовий антиспам: забороняємо URL у темі
        if re.search(r"(https?://|www\.)", value, flags=re.IGNORECASE):
            raise forms.ValidationError(_("Будь ласка, не додавайте посилання в тему повідомлення."))
        return value

    # ----- Повідомлення
    def clean_message(self):
        value = _normalize_ws(self.cleaned_data.get("message"))
        if len(value) < 10:
            raise forms.ValidationError(_("Повідомлення надто коротке (мін. 10 символів)."))
        if len(value) > 4000:
            raise forms.ValidationError(_("Повідомлення задовге (макс. 4000 символів)."))
        # приберемо контрольні символи (окрім переносу рядка)
        value = re.sub(r"[^\S\r\n]+", " ", value)  # стискаємо технічні пропуски
        return value

    # ----- Глобальна перевірка (опційно)
    def clean(self):
        cleaned = super().clean()
        # приклад: гарантуємо, що хоч один спосіб зв'язку валідний (email вже required),
        # але залишимо хук, якщо в майбутньому email стане необов'язковим:
        email = cleaned.get("email")
        phone = cleaned.get("phone")
        if not email and not phone:
            raise forms.ValidationError(_("Вкажіть принаймні електронну пошту або телефон."))
        return cleaned


