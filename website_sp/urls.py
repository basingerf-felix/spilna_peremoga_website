# website_sp/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.views.i18n import set_language

urlpatterns = [
    # Админка БЕЗ префикса языка
    path("admin/", admin.site.urls),

    # смена языка (как у тебя и было)
    path("i18n/setlang/", set_language, name="set_language"),
]

# Языкопрефикс только для публичных страниц
urlpatterns += i18n_patterns(
    path("", include("main.urls")),
    prefix_default_language=False,
)

# Медиа в dev
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
