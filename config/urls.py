from django.contrib import admin
from django.urls import path
from django.contrib.auth.views import LogoutView

from contracts.views import (
    dashboard,
    employee_login,
    contract_detail,
    contract_create,
    contract_edit,
    mark_notification_read,
    mark_all_notifications_read,
)

urlpatterns = [
    path("login/", employee_login, name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("", dashboard, name="dashboard"),
    path("contracts/<int:contract_id>/", contract_detail, name="contract_detail"),
    path("contracts/create/", contract_create, name="contract_create"),
    path("contracts/<int:contract_id>/edit/", contract_edit, name="contract_edit"),
    path("notifications/<int:notification_id>/read/", mark_notification_read, name="mark_notification_read"),
    path("notifications/read-all/", mark_all_notifications_read, name="mark_all_notifications_read"),
    path("admin/", admin.site.urls),
]
