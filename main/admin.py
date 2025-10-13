
from .models import ContactMessage, ProjectImage, ProjectBadge, Project, OrgUnit, ProjectDetail, ProjectDetailImage, \
    ProjectDetailGridImage

from django.contrib import admin, messages
from django.db import models
from django import forms
from django.urls import path, reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.html import format_html
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.core.files.storage import default_storage

from zipfile import ZipFile, BadZipFile
from django.core.files.base import ContentFile
import os

from .models import ProjectDetail, ProjectDetailImage

try:
    from PIL import Image  # Pillow для мягкой проверки
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False


@admin.register(OrgUnit)
class OrgUnitAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("created_at","first_name","last_name","email","subject")
    search_fields = ("first_name","last_name","email","subject","message")
    list_filter = ("created_at",)
    readonly_fields = ("created_at","ip","user_agent")

class ProjectDetailGridImageInline(admin.TabularInline):
    """Инлайн для полотна изображений (masonry)."""
    model = ProjectDetailGridImage
    extra = 0
    fields = ("image", "alt", "order")
    ordering = ("order", "id")
    show_change_link = True

# простая форма для ZIP
class BulkGridUploadForm(forms.Form):
    zip_file = forms.FileField(label=_("ZIP з зображеннями (для полотна)"))

class ProjectDetailImageInline(admin.TabularInline):
    model = ProjectDetailImage
    extra = 0
    fields = ("image", "alt", "order")
    ordering = ("order", "id")
    show_change_link = True



@admin.register(ProjectDetail)
class ProjectDetailAdmin(admin.ModelAdmin):
    list_display = ("slug", "title_override", "is_published", "created_at")
    list_filter = ("is_published",)
    search_fields = ("slug", "title_override", "lead", "body", "goal", "partners", "results")
    prepopulated_fields = {"slug": ("title_override",)}

    # ✅ добавили превью видео в readonly
    readonly_fields = ("bulk_upload_grid_link", "clear_grid_link", "video_admin_preview")

    inlines = [ProjectDetailImageInline, ProjectDetailGridImageInline]

    fieldsets = (
        (_("URL/Публікація"), {"fields": ("slug", "is_published")}),
        (_("Заголовки/Лід"), {"fields": ("title_override", "subtitle", "lead")}),
        (_("Контент"), {"fields": ("body",)}),
        # ✅ расширили медиаблок: video_file, video_poster, превью
        (_("Медіа"), {
            "fields": (
                "cover",
                "video_url",
                "video_file",
                "video_poster",
                "video_admin_preview",
                "bulk_upload_grid_link",
                "clear_grid_link",
            )
        }),
        (_("Блоки (override)"), {"fields": ("goal", "partners", "results")}),
        (_("SEO"), {"fields": ("seo_title", "seo_description", "og_image")}),
    )

    # --- Кнопка: загрузка полотна
    def bulk_upload_grid_link(self, obj):
        if not obj or not obj.pk:
            return _("Спершу збережіть об'єкт.")
        url = reverse(
            f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_bulk_upload_grid",
            args=[obj.pk],
        )
        return format_html('<a class="button" href="{}">{}</a>', url, _("Завантажити полотно (ZIP)"))
    bulk_upload_grid_link.short_description = _("Масове завантаження (полотно)")

    # --- Кнопка: очистить полотно
    def clear_grid_link(self, obj):
        if not obj or not obj.pk:
            return _("Спершу збережіть об'єкт.")
        url = reverse(
            f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_clear_grid",
            args=[obj.pk],
        )
        return format_html(
            '<a class="button" style="background:#8b0000;color:#fff;border-color:#8b0000" href="{}">{}</a>',
            url,
            _("Очистити полотно"),
        )
    clear_grid_link.short_description = _("Очистка полотна")

    # --- Превью видео в админке (readonly)
    def video_admin_preview(self, obj):
        if not obj:
            return ""
        # локальный файл
        if getattr(obj, "video_file", None):
            poster = obj.video_poster.url if getattr(obj, "video_poster", None) else ""
            poster_attr = format_html(' poster="{}"', poster) if poster else ""
            return format_html(
                '<video src="{}" style="max-width:480px;max-height:270px;" controls preload="metadata"{}></video>',
                obj.video_file.url,
                poster_attr
            )
        # ссылка (YouTube/Vimeo/MP4) — показываем сам URL как подсказку
        if getattr(obj, "video_url", ""):
            return format_html('<div style="max-width:520px;word-break:break-all;color:#555;">{}</div>', obj.video_url)
        return ""
    video_admin_preview.short_description = _("Прев’ю відео")

    # --- URL-ы
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:object_id>/bulk-upload-grid/",
                self.admin_site.admin_view(self.bulk_upload_grid),
                name=f"{self.model._meta.app_label}_{self.model._meta.model_name}_bulk_upload_grid",
            ),
            path(
                "<int:object_id>/clear-grid/",
                self.admin_site.admin_view(self.clear_grid),
                name=f"{self.model._meta.app_label}_{self.model._meta.model_name}_clear_grid",
            ),
        ]
        return custom + urls

    # --- Обработчик: очистить полотно
    def clear_grid(self, request, object_id: int):
        project = get_object_or_404(ProjectDetail, pk=object_id)
        deleted_count, details = ProjectDetailGridImage.objects.filter(project=project).delete()
        messages.success(request, _(f"Видалено {deleted_count} зображень з полотна."))
        return redirect(
            "admin:%s_%s_change" % (self.model._meta.app_label, self.model._meta.model_name),
            object_id,
        )

    # --- Обработчик: массовая загрузка полотна
    def bulk_upload_grid(self, request, object_id: int):
        project = get_object_or_404(ProjectDetail, pk=object_id)

        if request.method == "POST":
            form = BulkGridUploadForm(request.POST, request.FILES)
            if not form.is_valid():
                return self._render_bulk_upload_form(request, project, form)

            zf_file = form.cleaned_data["zip_file"]
            try:
                zf = ZipFile(zf_file)
            except BadZipFile:
                messages.error(request, _("Файл не є коректним ZIP-архівом."))
                return redirect(
                    "admin:%s_%s_change" % (self.model._meta.app_label, self.model._meta.model_name),
                    object_id,
                )

            created = 0
            stats = {
                "total": 0, "dirs": 0, "macosx": 0, "hiddenfork": 0,
                "bad_ext": 0, "empty": 0, "pillow_failed": 0, "saved": 0,
            }

            max_order = (
                ProjectDetailGridImage.objects.filter(project=project)
                .aggregate(max_o=models.Max("order"))["max_o"]
                or 0
            )

            allowed_ext = {".jpg", ".jpeg", ".png", ".webp"}

            for member in zf.namelist():
                # Папка?
                if member.endswith("/"):
                    stats["dirs"] += 1
                    continue
                stats["total"] += 1

                # Мусор macOS
                top = member.split("/", 1)[0]
                name_in_zip = os.path.basename(member)
                if top == "__MACOSX":
                    stats["macosx"] += 1
                    continue
                if name_in_zip.startswith("._"):
                    stats["hiddenfork"] += 1
                    continue

                base, ext = os.path.splitext(name_in_zip)
                ext = (ext or "").lower().strip()
                if ext not in allowed_ext:
                    stats["bad_ext"] += 1
                    continue

                # Читаем данные
                try:
                    data = zf.read(member)
                except KeyError:
                    stats["empty"] += 1
                    continue
                if not data:
                    stats["empty"] += 1
                    continue

                # Мягкая проверка через Pillow (не блокирующая)
                if PIL_AVAILABLE:
                    try:
                        Image.open(BytesIO(data)).verify()
                    except Exception:
                        stats["pillow_failed"] += 1
                        # всё равно принимаем файл

                # Уникальное имя
                safe_base = slugify(base) or "image"
                filename = f"{safe_base}{ext}"
                filename = default_storage.get_available_name(filename)

                # Сохраняем запись (alt пустой)
                obj = ProjectDetailGridImage(
                    project=project,
                    order=max_order + 1,
                    alt="",
                )
                obj.image.save(filename, ContentFile(data), save=True)
                max_order += 1
                created += 1
                stats["saved"] += 1

            zf.close()

            if created:
                messages.success(request, _(f"Додано зображень до полотна: {created}."))
            else:
                messages.warning(request, _("У архіві не знайдено зображень (jpg/jpeg/png/webp)."))

            # Диагностика
            messages.info(
                request,
                _(
                    "Підсумок: всього файлів: {total}, папок: {dirs}, macOS: {macosx}, ._форки: {hiddenfork}, "
                    "інший розширення: {bad_ext}, порожніх/недоступних: {empty}, Pillow помилок: {pillow_failed}, збережено: {saved}"
                ).format(**stats)
            )

            return redirect(
                "admin:%s_%s_change" % (self.model._meta.app_label, self.model._meta.model_name),
                object_id,
            )

        # GET → форма
        form = BulkGridUploadForm()
        return self._render_bulk_upload_form(request, project, form)

    def _render_bulk_upload_form(self, request, project, form):
        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "original": project,
            "title": _("Завантаження полотна (ZIP)"),
            "form": form,
        }
        return render(request, "admin/projectdetail/bulk_upload_images.html", context)


class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 0
    fields = ("image", "alt", "order")
    ordering = ("order", "id")
    show_change_link = True

class ProjectBadgeInline(admin.TabularInline):
    model = ProjectBadge
    extra = 0
    fields = ("text", "order")
    ordering = ("order", "id")

# main/admin.py (фрагмент)
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "order", "is_reverse",
                    "is_reverse_platform", "is_reverse_education", "is_reverse_sport")
    list_filter = ("is_published",)
    search_fields = ("title", "description", "goal", "partners", "results")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("units",)  # можно оставить, т.к. мы НЕ используем through
    inlines = [ProjectImageInline, ProjectBadgeInline]
    ordering = ("order", "id")
    autocomplete_fields = ("detail",)


    def units_list(self, obj):
        return ", ".join(u.name for u in obj.units.all())

    units_list.short_description = "Підрозділи"