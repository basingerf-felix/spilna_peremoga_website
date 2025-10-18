from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path("projects/", views.ProjectsListView.as_view(), name="projects"),
    path("projects/<slug:slug>/", views.ProjectDetailView.as_view(), name="project_detail"),
    path("go-spilna-peremoga/", views.SubdivisionView.as_view(), name="go-spilna-peremoga"),
    path("go_creative_agency/", views.EducationUnitView.as_view(), name="go-creative-agency"),
    path("go_sp_productio/", views.SportsUnitView.as_view(), name="go-sp-production"),
]
