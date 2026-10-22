from django.conf import settings
from django.db import models


class Contract(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Dự thảo"
        ACTIVE = "ACTIVE", "Đang hiệu lực"
        EXPIRED = "EXPIRED", "Hết hạn"
        TERMINATED = "TERMINATED", "Đã thanh lý"

    code = models.CharField("Mã hợp đồng", max_length=30, unique=True)
    name = models.CharField("Tên hợp đồng", max_length=255)
    partner = models.CharField("Đối tác ký kết", max_length=255)
    signed_date = models.DateField("Ngày ký", null=True, blank=True)
    effective_date = models.DateField("Ngày có hiệu lực", null=True, blank=True)
    expiry_date = models.DateField("Ngày hết hạn", null=True, blank=True)
    value = models.DecimalField(
        "Giá trị hợp đồng",
        max_digits=18,
        decimal_places=2,
        default=0,
    )
    status = models.CharField(
        "Trạng thái",
        max_length=15,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    description = models.TextField("Nội dung hợp đồng", blank=True)
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    updated_at = models.DateTimeField("Ngày cập nhật", auto_now=True)

    class Meta:
        verbose_name = "Hợp đồng"
        verbose_name_plural = "Quản lý hợp đồng"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class UserProfile(models.Model):
    class Role(models.TextChoices):
        MANAGER = "MANAGER", "Quản lý"
        STAFF = "STAFF", "Nhân viên"
        CUSTOMER = "CUSTOMER", "Khách hàng"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Tài khoản",
    )
    role = models.CharField(
        "Vai trò",
        max_length=20,
        choices=Role.choices,
        default=Role.STAFF,
    )
    partner_name = models.CharField(
        "Tên đối tác / Doanh nghiệp khách hàng",
        max_length=255,
        blank=True,
        default="",
        help_text="Chỉ định đối tác mà tài khoản khách hàng đại diện để phân quyền dữ liệu",
    )
    phone = models.CharField("Số điện thoại", max_length=20, blank=True, default="")
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    updated_at = models.DateTimeField("Ngày cập nhật", auto_now=True)

    class Meta:
        verbose_name = "Hồ sơ người dùng"
        verbose_name_plural = "Quản lý hồ sơ người dùng"

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        EXPIRING = "EXPIRING", "Sắp hết hạn"
        EXPIRED = "EXPIRED", "Đã hết hạn"
        DRAFT = "DRAFT", "Chờ xử lý / Dự thảo"
        SYSTEM = "SYSTEM", "Hệ thống"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
        verbose_name="Người nhận",
        help_text="Người nhận cụ thể, hoặc để trống nếu là thông báo chung cho bộ phận quản lý/nhân viên",
    )
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
        verbose_name="Hợp đồng liên quan",
    )
    title = models.CharField("Tiêu đề", max_length=255)
    message = models.TextField("Nội dung thông báo")
    notification_type = models.CharField(
        "Loại thông báo",
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
    )
    is_read = models.BooleanField("Đã đọc", default=False)
    created_at = models.DateTimeField("Thời gian tạo", auto_now_add=True)

    class Meta:
        verbose_name = "Thông báo"
        verbose_name_plural = "Quản lý thông báo"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_notification_type_display()}] {self.title}"
