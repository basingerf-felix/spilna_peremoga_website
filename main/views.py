from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.db.models import Prefetch
from django.shortcuts import render, redirect
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
from django.views import View
from django.views.generic import TemplateView, DetailView
import requests

from .emailing import send_contact_emails
from .forms import ContactForm
from .models import Project, OrgUnit, ProjectDetail


def index(request):
    form = ContactForm()
    if request.method == "POST" and request.POST.get("form_name") == "contact":
        form = ContactForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.ip = request.META.get("REMOTE_ADDR")
            obj.user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]
            obj.save()

            # формируем контекст для писем
            ctx = {
                "first_name": obj.first_name,
                "last_name": obj.last_name,
                "email": obj.email,
                "phone": obj.phone,
                "subject": obj.subject,
                "message": obj.message,
                "ip": obj.ip,
                "user_agent": obj.user_agent,
            }

            try:
                ok, info = send_contact_emails(ctx)
                if ok:
                    messages.success(request, _("Дякуємо! Повідомлення надіслано."))
                else:
                    messages.warning(request, _("Повідомлення збережено, але лист не надіслано (%(err)s).") % {"err": info})
            except Exception:
                messages.warning(request, _("Повідомлення збережено, але лист не надіслано. Спробуйте пізніше."))

            return redirect("/#contact")
        else:
            messages.error(request, _("Перевірте поля та спробуйте знову."))
    return render(request, "main/index.html", {"contact_form": form})


class ProjectsListView(TemplateView):
    template_name = "main/projects.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = Project.objects.filter(is_published=True).prefetch_related(
            "badges",
            Prefetch("images"),
            "units",
        ).order_by("order", "id")

        # ?unit=slug  ИЛИ  ?units=slug1,slug2
        unit = self.request.GET.get("unit")
        units = self.request.GET.get("units")
        if unit:
            qs = qs.filter(units__slug=unit)
        elif units:
            slugs = [s.strip() for s in units.split(",") if s.strip()]
            if slugs:
                qs = qs.filter(units__slug__in=slugs).distinct()

        ctx["projects"] = qs
        ctx["all_units"] = OrgUnit.objects.all()
        ctx["active_units"] = (units.split(",") if units else ([unit] if unit else []))
        return ctx


class ProjectDetailView(DetailView):
    template_name = "main/project_detail.html"
    model = ProjectDetail
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return (ProjectDetail.objects
                .filter(is_published=True)
                .prefetch_related("images"))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Связанный «демо» проект (нужен для бейджей/units, если надо)
        ctx["project"] = getattr(self.object, "project", None)
        return ctx


class AboutView(TemplateView):
    template_name = "main/about.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Приклад динаміки без БД (за потреби — заміниш на ORM-моделі нижче)
        ctx["team"] = [
            {
                "name": "Володимир Бульба",
                "role": "Засновник платформи. Майстер спорту міжнародного класу. Радник Міністра молоді та спорту (2015–2019).",
                "photo": "images/bulba_vol.webp",
            },
            {
                "name": "Олександр Соколинський",
                "role": "Співзасновник. Менеджер спортивно-молодіжних подій, громадський діяч, спортивний директор НКРУ.",
                "photo": "images/sokolinskiy_al.webp",
            },
            {
                "name": "Валерія Іваненко",
                "role": "Директор «Спільна Перемога Продакшн». Продюсер, член спілок кінематографістів та журналістів.",
                "photo": "images/ivanenko_val.webp",
            },
        ]
        return ctx


class UnitProjectsMixin:
    """
    Простой миксин: выбираем проекты юнита и подмешиваем флаг page_is_reverse
    из нужного поля проекта (страничное поле приоритетнее глобального).
    """
    template_name = "main/unit_projects.html"  # или свой
    unit_slug = None
    reverse_field = None  # имя булевого поля на Project

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        unit = OrgUnit.objects.filter(slug=self.unit_slug).first()
        ctx["unit"] = unit

        qs = (
            Project.objects.filter(is_published=True, units__slug=self.unit_slug)
            .prefetch_related("badges", Prefetch("images"))
            .order_by("order", "id")
            .distinct()
        )

        # Страничное поле — главнее глобального. Если reverse_field задан,
        # то используем его значение как есть (True/False).
        # Если reverse_field не задан — используем глобальный is_reverse.
        if self.reverse_field:
            for p in qs:
                page_val = getattr(p, self.reverse_field, False)  # BoolField: всегда True/False
                setattr(p, "page_is_reverse", bool(page_val))
        else:
            for p in qs:
                setattr(p, "page_is_reverse", bool(p.is_reverse))

        ctx["projects"] = qs
        return ctx


# Конкретные страницы (замени слаги и поля под себя)
class SubdivisionView(UnitProjectsMixin, TemplateView):
    template_name  = "main/go_spilna_peremoga.html"
    unit_slug      = "gromadska-organizaciya-spilna-peremoga"
    reverse_field  = "is_reverse_platform"

class EducationUnitView(UnitProjectsMixin, TemplateView):
    template_name  = "main/go_creative_agency.html"
    unit_slug      = "tov-kreativna-agenciya-brspilna-peremoga"
    reverse_field  = "is_reverse_education"

class SportsUnitView(UnitProjectsMixin, TemplateView):
    template_name  = "main/go_sp_production.html"
    unit_slug      = "prodakshn-studiya-brspilna-peremoga"
    reverse_field  = "is_reverse_sport"