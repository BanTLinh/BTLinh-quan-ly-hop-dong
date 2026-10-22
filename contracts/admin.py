from django.contrib import admin
from .models import Contract, UserProfile, Notification


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "partner",
        "signed_date",
        "expiry_date",
        "value",
        "status",
    )
    list_filter = ("status", "signed_date", "expiry_date")
    search_fields = ("code", "name", "partner")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "partner_name", "phone", "created_at")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email", "partner_name", "phone")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "notification_type", "user", "contract", "is_read", "created_at")
    list_filter = ("notification_type", "is_read", "created_at")
    search_fields = ("title", "message", "contract__code")
    ordering = ("-created_at",)


admin.site.site_header = "HỆ THỐNG QUẢN LÝ HỢP ĐỒNG"
admin.site.site_title = "Quản trị hợp đồng"
admin.site.index_title = "TRANG QUẢN TRỊ HỢP ĐỒNG"
