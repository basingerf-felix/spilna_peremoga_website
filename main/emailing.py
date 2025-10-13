from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def send_contact_emails(context: dict):
    """
    Шлёт два письма:
    1) Менеджеру (CONTACT_RECIPIENT) — полная заявка.
    2) Автоответ пользователю — аккуратное подтверждение.
    """
    manager_to = getattr(settings, "CONTACT_RECIPIENT", None)
    if not manager_to:
        return False, "CONTACT_RECIPIENT is not set"

    # --- письмо менеджеру ---
    subj_manager = f"[Contact] {context.get('subject', '(no subject)')}"
    html_manager = render_to_string("main/contact_to_manager.html", context)
    text_manager = strip_tags(html_manager)

    msg1 = EmailMultiAlternatives(
        subject=subj_manager,
        body=text_manager,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[manager_to],
        reply_to=[context.get("email")] if context.get("email") else None,
    )
    msg1.attach_alternative(html_manager, "text/html")
    msg1.send(fail_silently=False)

    # --- автоответ пользователю (не обязателен) ---
    user_email = context.get("email")
    if user_email:
        subj_user = "Дякуємо за звернення — Spilna Peremoga"
        html_user = render_to_string("main/contact_autoreply.html", context)
        text_user = strip_tags(html_user)
        msg2 = EmailMultiAlternatives(
            subject=subj_user,
            body=text_user,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user_email],
        )
        msg2.attach_alternative(html_user, "text/html")
        msg2.send(fail_silently=True)

    return True, "ok"
