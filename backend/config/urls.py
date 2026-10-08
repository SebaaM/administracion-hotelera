"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from pms import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/session/", views.session),
    path("api/login/", views.signin),
    path("api/logout/", views.signout),
    path("api/state/", views.state),
    path("api/settings/", views.configure),
    path("api/reservations/", views.reservations),
    path("api/reservations/<int:pk>/", views.reservation),
    path("api/reservations/<int:pk>/ledger/", views.ledger),
    path("api/reservations/<int:pk>/<str:action>/", views.reservation_action),
    path("api/rooms/", views.rooms),
    path("api/rooms/<int:pk>/", views.room),
    path("api/rooms/<int:pk>/units/", views.add_unit),
    path("api/units/<int:pk>/", views.unit),
    path("api/cleaning/", views.cleaning),
    path("api/cleaning/<int:pk>/", views.cleaning_action),
    path("api/maintenance/", views.maintenance),
    path("api/maintenance/<int:pk>/", views.maintenance_action),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
