from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator


class ContactMessage(models.Model):
    first_name = models.CharField(max_length=80)
    last_name  = models.CharField(max_length=80, blank=True)
    email      = models.EmailField()
    phone      = models.CharField(max_length=40, blank=True)
    subject    = models.CharField(max_length=160)
    message    = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    ip         = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.first_name} {self.last_name} — {self.subject}"


class OrgUnit(models.Model):
    name = models.CharField(_("Підрозділ"), max_length=120, unique=True)
    slug = models.SlugField(_("Слаг"), max_length=120, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("Підрозділ організації")
        verbose_name_plural = _("Підрозділи організації")

    def __str__(self):
        return self.name


class ProjectDetail(models.Model):
    # URL
    slug = models.SlugField(_("Слаг детальної сторінки"), unique=True, max_length=255)

    # Заголовки/лід (можно переопределять то, что в Project)
    title_override = models.CharField(_("Заголовок (детально)"), max_length=255, blank=True)
    subtitle = models.CharField(_("Підзаголовок"), max_length=255, blank=True)
    lead = models.TextField(_("Короткий лід/опис"), blank=True)

    # Контент
    body = models.TextField(_("Детальний опис (HTML дозволено)"), blank=True)

    # Медіа
    cover = models.ImageField(_("Обкладинка (герой)"), upload_to="projects/detail/", blank=True, null=True)
    video_url = models.URLField(_("Відео (YouTube/Vimeo/MP4)"), blank=True)

    # ✅ Новое: собственный файл и постер (обложка)
    video_file = models.FileField(
        _("Відеофайл"),
        upload_to="projects/detail/video/",
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=["mp4", "webm", "ogg"])]
    )
    video_poster = models.ImageField(
        _("Обкладинка відео (poster)"),
        upload_to="projects/detail/video/posters/",
        blank=True,
        null=True
    )

    # (опціонально) дубль блоків з можливістю перезапису
    goal = models.TextField(_("Мета (override)"), blank=True)
    partners = models.TextField(_("Партнери (override)"), blank=True)
    results = models.TextField(_("Результати (override)"), blank=True)

    # SEO
    seo_title = models.CharField(_("SEO title"), max_length=255, blank=True)
    seo_description = models.TextField(_("SEO description"), blank=True)
    og_image = models.ImageField(_("OG image"), upload_to="projects/detail/og/", blank=True, null=True)

    is_published = models.BooleanField(_("Опубліковано"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Детальна сторінка проєкту")
        verbose_name_plural = _("Детальні сторінки проєктів")

    def __str__(self):
        return self.title_override or self.slug

class ProjectDetailGridImage(models.Model):
    """Изображения для «полотна» (masonry) внизу страницы проекта."""
    project = models.ForeignKey(
        ProjectDetail,
        on_delete=models.CASCADE,
        related_name="grid_images",
        verbose_name=_("Проєкт"),
    )
    image = models.ImageField(upload_to="projects/grid/", verbose_name=_("Зображення"))
    alt = models.CharField(_("ALT"), max_length=255, blank=True)
    order = models.PositiveIntegerField(_("Порядок"), default=0, db_index=True)

    class Meta:
        verbose_name = _("Зображення полотна")
        verbose_name_plural = _("Зображення полотна")
        ordering = ("order", "id")

    def __str__(self):
        return self.alt or f"Фото #{self.pk}"


class ProjectDetailImage(models.Model):
    detail = models.ForeignKey(ProjectDetail, on_delete=models.CASCADE, related_name="images", verbose_name=_("Проєкт (детально)"))
    image = models.ImageField(upload_to="projects/detail/gallery/")
    alt = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("Зображення (детально)")
        verbose_name_plural = _("Галерея (детально)")

    def __str__(self):
        return f"{self.detail} #{self.pk}"

# main/models.py (фрагмент)
class Project(models.Model):
    title = models.CharField(_("Назва проєкту"), max_length=255)
    description = models.TextField(_("Опис"), help_text=_("Основний опис/лід для картки"))
    goal = models.TextField(_("Мета"), blank=True, help_text=_("Текст для блоку «Мета»"))
    partners = models.TextField(_("Партнери"), blank=True, help_text=_("Текст для блоку «Партнери»"))
    results = models.TextField(_("Результати"), blank=True, help_text=_("Текст для блоку «Результати»"))

    # Глобальный реверс — как и было
    is_reverse = models.BooleanField(
        _("Реверсувати макет (текст зліва, фото справа)"),
        default=False
    )

    # ✅ НОВОЕ: простые флажки для отдельных страниц підрозділів
    # Переименуй поля под свои реальные страницы/слаги
    is_reverse_platform = models.BooleanField(
        _("Реверс для сторінки: Громадська платформа"),
        default=False
    )
    is_reverse_education = models.BooleanField(
        _("Реверс для сторінки: Освіта"),
        default=False
    )
    is_reverse_sport = models.BooleanField(
        _("Реверс для сторінки: Спорт"),
        default=False
    )

    is_published = models.BooleanField(_("Опубліковано"), default=True)
    order = models.PositiveIntegerField(_("Порядок"), default=0, db_index=True)

    units = models.ManyToManyField(
        OrgUnit,
        verbose_name=_("Підрозділи"),
        related_name="projects",
        blank=True,
    )

    detail = models.OneToOneField(
        ProjectDetail,
        on_delete=models.SET_NULL,
        related_name="project",
        verbose_name=_("Детальна сторінка"),
        null=True, blank=True,
        help_text=_("Опціонально: прив’яжіть детальну сторінку для «Дізнатися більше».")
    )

    slug = models.SlugField(_("Слаг"), unique=True, max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "-created_at"]
        verbose_name = _("Проєкт")
        verbose_name_plural = _("Проєкти")

    def __str__(self):
        return self.title


class ProjectImage(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(_("Зображення"), upload_to="projects/")
    alt = models.CharField(_("Alt (опис зображення)"), max_length=255, blank=True)
    order = models.PositiveIntegerField(_("Порядок"), default=0, db_index=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("Зображення проєкту")
        verbose_name_plural = _("Зображення проєкту")

    def __str__(self):
        return f"{self.project.title} [{self.order}]"


class ProjectBadge(models.Model):
    """Бейдж на фото: рік/період/місто тощо — довільний текст."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="badges")
    text = models.CharField(_("Текст бейджа"), max_length=100)
    order = models.PositiveIntegerField(_("Порядок"), default=0, db_index=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("Бейдж проєкту")
        verbose_name_plural = _("Бейджі проєкту")

    def __str__(self):
        return f"{self.text} ({self.project.title})"



