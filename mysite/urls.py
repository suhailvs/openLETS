"""
URL configuration for mysite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.urls import path, include
from openletsweb import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", views.index, name="index"),
    path("home/", views.home, name="home"),
    path("settings/", views.settings, name="settings"),
    path("transaction/new/", views.transaction_new, name="transaction_new"),
    path("transaction/list/", views.transaction_list, name="transaction_list"),
    path(
        "transaction/confirm/<int:trans_record_id>/",
        views.transaction_confirm,
        name="transaction_confirm",
    ),
    path(
        "transaction/modify/<int:trans_record_id>/",
        views.transaction_modify,
        name="transaction_modify",
    ),
    path(
        "transaction/reject/<int:trans_record_id>/",
        views.transaction_reject,
        name="transaction_reject",
    ),
    path("settings/user/update/", views.user_update, name="user_update"),
    path("settings/user/new/", views.SignUpView.as_view(), name="user_new"),
    path("settings/person/update/", views.person_update, name="person_update"),
    path("exchange_rate/new/", views.exchange_rate_new, name="exchange_rate_new"),
    path(
        "exchange_rate/delete/<int:rate_id>/",
        views.exchange_rate_delete,
        name="exchange_rate_delete",
    ),
    path("export_data/", views.export_data, name="export_data"),
    path("about/", views.content_view, {"name": "about"}, "about"),
    path("contact/", views.content_view, {"name": "contact"}, "contact"),
    path("news/", views.news, name="news"),
]
