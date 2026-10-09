from django.urls import path
from . import views
urlpatterns=[
    path("profiles/",views.profiles),
    path("profiles/<int:pk>/",views.profile),
    path("drafts/",views.drafts),
    path("drafts/<int:pk>/",views.draft),
    path("drafts/<int:pk>/preview/",views.preview),
    path("drafts/<int:pk>/apply/",views.apply),
    path("drafts/<int:pk>/discard/",views.discard),
    path("drafts/<int:pk>/csv/",views.export_csv),
]
