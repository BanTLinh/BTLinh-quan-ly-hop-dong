from datetime import timedelta
from decimal import Decimal

from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.contrib import messages

from .models import Contract, UserProfile, Notification


def get_user_role_and_partner(user):
    """
    Xác định vai trò nghiệp vụ và tên công ty đối tác (nếu là khách hàng).
    """
    if not user.is_authenticated:
        return "ANONYMOUS", ""
    if user.is_superuser:
        return UserProfile.Role.MANAGER, ""
    if hasattr(user, "profile"):
        return user.profile.role, user.profile.partner_name
    if user.groups.filter(name="Quan ly").exists():
        return UserProfile.Role.MANAGER, ""
    if user.groups.filter(name="Khach hang").exists():
        return UserProfile.Role.CUSTOMER, ""
    return UserProfile.Role.STAFF, ""


def sync_contract_notifications():
    """
    Tự động đồng bộ thông báo thời hạn dựa trên dữ liệu hợp đồng thực tế.
    Không tạo thông báo giả; không tạo trùng lặp.
    """
    today = timezone.localdate()

    # 1. Hợp đồng sắp hết hạn (<= 30 ngày)
    expiring = Contract.objects.filter(
        status=Contract.Status.ACTIVE,
        expiry_date__gte=today,
        expiry_date__lte=today + timedelta(days=30),
    )
    for c in expiring:
        days_left = (c.expiry_date - today).days
        Notification.objects.get_or_create(
            contract=c,
            notification_type=Notification.NotificationType.EXPIRING,
            defaults={
                "title": f"Hợp đồng {c.code} sắp hết hạn",
                "message": (
                    f"Hợp đồng '{c.name}' (Đối tác: {c.partner}) sẽ hết hạn vào ngày "
                    f"{c.expiry_date.strftime('%d/%m/%Y')} (còn {days_left} ngày). "
                    "Cần rà soát gia hạn hoặc chuẩn bị thủ tục thanh lý."
                ),
                "is_read": False,
            },
        )

    # 2. Hợp đồng đã hết hạn (status EXPIRED hoặc expiry_date < today)
    expired = Contract.objects.filter(
        Q(status=Contract.Status.EXPIRED) | Q(expiry_date__lt=today)
    ).exclude(status=Contract.Status.TERMINATED)
    for c in expired:
        Notification.objects.get_or_create(
            contract=c,
            notification_type=Notification.NotificationType.EXPIRED,
            defaults={
                "title": f"Hợp đồng {c.code} đã hết hạn",
                "message": (
                    f"Hợp đồng '{c.name}' (Đối tác: {c.partner}) đã hết hạn từ ngày "
                    f"{c.expiry_date.strftime('%d/%m/%Y') if c.expiry_date else 'chưa xác định'}. "
                    "Vui lòng hoàn tất nghĩa vụ và tiến hành thanh lý hợp đồng."
                ),
                "is_read": False,
            },
        )

    # 3. Hợp đồng dự thảo (chờ xử lý)
    drafts = Contract.objects.filter(status=Contract.Status.DRAFT)
    for c in drafts:
        Notification.objects.get_or_create(
            contract=c,
            notification_type=Notification.NotificationType.DRAFT,
            defaults={
                "title": f"Hợp đồng {c.code} ở trạng thái Dự thảo",
                "message": (
                    f"Hợp đồng '{c.name}' (Đối tác: {c.partner}) hiện đang ở trạng thái Dự thảo, "
                    "chờ hoàn thiện thông tin ký kết và phê duyệt hiệu lực."
                ),
                "is_read": False,
            },
        )


def employee_login(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    # Chỉ hiển thị tài khoản dùng thử trong môi trường phát triển/demo nội bộ (DEBUG=True)
    from django.conf import settings
    from django.contrib.auth import get_user_model
    User = get_user_model()
    demo_configs = [
        {
            "role_name": "Quản lý",
            "role_key": "MANAGER",
            "username": "quanly_test",
            "password": "QuanLy@Secure2026",
            "desc": "Toàn quyền quản trị & xem toàn bộ 4 hợp đồng",
            "badge_class": "badge-manager",
        },
        {
            "role_name": "Nhân viên",
            "role_key": "STAFF",
            "username": "nhanvien_kd",
            "password": "NhanVien@Secure2026",
            "desc": "Nghiệp vụ hợp đồng & tạo/chỉnh sửa hồ sơ",
            "badge_class": "badge-staff",
        },
    ]

    verified_demo_accounts = []
    # Bảo vệ: Chỉ hiển thị khi đang bật chế độ phát triển nội bộ
    if getattr(settings, "DEBUG", False):
        configured_usernames = [d["username"] for d in demo_configs]
        existing_users = set(
            User.objects.filter(username__in=configured_usernames, is_active=True).values_list("username", flat=True)
        )

        for cfg in demo_configs:
            # Chỉ hiển thị khi tài khoản tồn tại và xác minh đăng nhập thành công
            if cfg["username"] in existing_users:
                test_auth = authenticate(request, username=cfg["username"], password=cfg["password"])
                if test_auth is not None:
                    verified_demo_accounts.append(cfg)

    error = False
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            destination = request.POST.get("next", "")
            if destination.startswith("/") and not destination.startswith("//"):
                return redirect(destination)
            return redirect("dashboard")
        error = True

    return render(
        request,
        "contracts/login.html",
        {
            "error": error,
            "form": {"errors": error},
            "demo_accounts": verified_demo_accounts,
        },
    )


@login_required
def dashboard(request):
    # Đồng bộ thông báo thực tế
    sync_contract_notifications()

    user_role, partner_name = get_user_role_and_partner(request.user)
    today = timezone.localdate()

    # Phân quyền dữ liệu hợp đồng:
    # Khách hàng chỉ xem hợp đồng có đối tác trùng với công ty của họ
    if user_role == UserProfile.Role.CUSTOMER:
        all_contracts = Contract.objects.filter(partner=partner_name)
    else:
        all_contracts = Contract.objects.all()

    # Thống kê tổng quan dựa trên tập dữ liệu được phân quyền
    total = all_contracts.count()
    active = all_contracts.filter(status=Contract.Status.ACTIVE).count()
    draft = all_contracts.filter(status=Contract.Status.DRAFT).count()
    terminated = all_contracts.filter(status=Contract.Status.TERMINATED).count()

    expired = all_contracts.filter(
        expiry_date__lt=today
    ).exclude(status=Contract.Status.TERMINATED).count()

    expiring_queryset = all_contracts.filter(
        status=Contract.Status.ACTIVE,
        expiry_date__gte=today,
        expiry_date__lte=today + timedelta(days=30),
    ).order_by("expiry_date")

    expiring_count = expiring_queryset.count()

    # Tìm kiếm và lọc danh sách
    contracts = all_contracts
    keyword = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    expiry_filter = request.GET.get("expiry", "").strip()
    sort = request.GET.get("sort", "-created_at").strip()

    if keyword:
        contracts = contracts.filter(
            Q(code__icontains=keyword)
            | Q(name__icontains=keyword)
            | Q(partner__icontains=keyword)
        )

    valid_statuses = {choice[0] for choice in Contract.Status.choices}
    if status_filter in valid_statuses:
        contracts = contracts.filter(status=status_filter)

    if expiry_filter == "expiring":
        contracts = contracts.filter(
            expiry_date__gte=today,
            expiry_date__lte=today + timedelta(days=30),
        )
    elif expiry_filter == "expired":
        contracts = contracts.filter(expiry_date__lt=today)
    elif expiry_filter == "no_expiry":
        contracts = contracts.filter(expiry_date__isnull=True)

    allowed_sorts = {
        "-created_at", "created_at", "code", "-code",
        "expiry_date", "-expiry_date", "value", "-value",
        "name", "-name",
    }
    if sort not in allowed_sorts:
        sort = "-created_at"

    contracts = contracts.order_by(sort)

    paginator = Paginator(contracts, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Dữ liệu biểu đồ trạng thái
    status_counts = all_contracts.values("status").annotate(count=Count("id"))
    counts_by_status = {item["status"]: item["count"] for item in status_counts}

    chart_data = [
        {
            "label": label,
            "count": counts_by_status.get(value, 0),
            "color": color,
        }
        for value, label, color in [
            (Contract.Status.ACTIVE, "Đang hiệu lực", "#168b82"),
            (Contract.Status.DRAFT, "Dự thảo", "#d9a441"),
            (Contract.Status.EXPIRED, "Hết hạn", "#d96c6c"),
            (Contract.Status.TERMINATED, "Đã thanh lý", "#8091a7"),
        ]
    ]

    # Lấy thông báo theo phân quyền người dùng
    if user_role == UserProfile.Role.CUSTOMER:
        notifications_qs = Notification.objects.filter(
            Q(contract__partner=partner_name) | Q(user=request.user)
        ).select_related("contract").order_by("-created_at")
    else:
        notifications_qs = Notification.objects.filter(
            Q(user=request.user) | Q(user__isnull=True)
        ).select_related("contract").order_by("-created_at")

    unread_notifications_count = notifications_qs.filter(is_read=False).count()
    notifications_list = list(notifications_qs[:15])

    context = {
        "user_role": user_role,
        "partner_name": partner_name,
        "total": total,
        "active": active,
        "draft": draft,
        "expired": expired,
        "terminated": terminated,
        "expiring_count": expiring_count,
        "expiring_contracts": expiring_queryset[:5],
        "contracts": page_obj.object_list,
        "page_obj": page_obj,
        "status_choices": Contract.Status.choices,
        "keyword": keyword,
        "status_filter": status_filter,
        "expiry_filter": expiry_filter,
        "sort": sort,
        "chart_data": chart_data,
        "notifications": notifications_list,
        "unread_notifications_count": unread_notifications_count,
        "can_create_contract": user_role in [UserProfile.Role.MANAGER, UserProfile.Role.STAFF],
        "can_edit_contract": (
            user_role == UserProfile.Role.MANAGER
            or (user_role == UserProfile.Role.STAFF and request.user.has_perm("contracts.change_contract"))
        ),
    }

    return render(request, "contracts/dashboard.html", context)


@login_required
def contract_detail(request, contract_id):
    """
    Xem chi tiết hợp đồng kèm kiểm tra phân quyền phía máy chủ (Server-side check).
    Chặn triệt để hành vi can thiệp ID URL (ID Tampering).
    """
    contract = get_object_or_404(Contract, id=contract_id)
    user_role, partner_name = get_user_role_and_partner(request.user)

    # Kiểm tra quyền truy cập:
    # Khách hàng chỉ được phép xem hợp đồng của đúng công ty mình
    if user_role == UserProfile.Role.CUSTOMER:
        if contract.partner != partner_name:
            raise PermissionDenied(
                "Bạn không có quyền truy cập hợp đồng của đối tác khác. "
                "Hành vi thay đổi ID trên URL đã bị máy chủ chặn lại."
            )

    can_edit = (
        user_role == UserProfile.Role.MANAGER
        or (user_role == UserProfile.Role.STAFF and request.user.has_perm("contracts.change_contract"))
    )

    context = {
        "contract": contract,
        "user_role": user_role,
        "partner_name": partner_name,
        "can_edit": can_edit,
    }
    return render(request, "contracts/contract_detail.html", context)


@login_required
def contract_create(request):
    """
    Tạo hợp đồng mới với kiểm soát phân quyền: Chỉ Quản lý và Nhân viên được cấp quyền.
    Khách hàng bị từ chối truy cập.
    """
    user_role, _ = get_user_role_and_partner(request.user)
    if user_role == UserProfile.Role.CUSTOMER:
        raise PermissionDenied("Khách hàng không có quyền tạo hợp đồng mới.")
    if user_role == UserProfile.Role.STAFF and not request.user.has_perm("contracts.add_contract"):
        raise PermissionDenied("Bạn không có quyền thêm hợp đồng mới.")

    errors = {}
    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        name = request.POST.get("name", "").strip()
        partner = request.POST.get("partner", "").strip()
        signed_date = request.POST.get("signed_date") or None
        effective_date = request.POST.get("effective_date") or None
        expiry_date = request.POST.get("expiry_date") or None
        value_raw = request.POST.get("value", "0").replace(",", "").strip()
        status = request.POST.get("status", Contract.Status.DRAFT)
        description = request.POST.get("description", "").strip()

        if not code:
            errors["code"] = "Vui lòng nhập mã hợp đồng."
        elif Contract.objects.filter(code=code).exists():
            errors["code"] = "Mã hợp đồng này đã tồn tại trong hệ thống."

        if not name:
            errors["name"] = "Vui lòng nhập tên hợp đồng."
        if not partner:
            errors["partner"] = "Vui lòng nhập tên đối tác ký kết."

        try:
            value = Decimal(value_raw)
            if value < 0:
                errors["value"] = "Giá trị hợp đồng không thể âm."
        except Exception:
            errors["value"] = "Giá trị hợp đồng không hợp lệ."
            value = Decimal(0)

        if not errors:
            contract = Contract.objects.create(
                code=code,
                name=name,
                partner=partner,
                signed_date=signed_date,
                effective_date=effective_date,
                expiry_date=expiry_date,
                value=value,
                status=status,
                description=description,
            )
            # Tạo thông báo hệ thống
            Notification.objects.create(
                contract=contract,
                notification_type=Notification.NotificationType.SYSTEM,
                title=f"Hợp đồng mới: {contract.code}",
                message=f"Hợp đồng '{contract.name}' (Đối tác: {contract.partner}) đã được tạo bởi {request.user.username}.",
                is_read=False,
            )
            messages.success(request, f"Đã tạo thành công hợp đồng {contract.code}!")
            return redirect("contract_detail", contract_id=contract.id)

    context = {
        "status_choices": Contract.Status.choices,
        "errors": errors,
        "is_edit": False,
        "contract": request.POST if request.method == "POST" else None,
    }
    return render(request, "contracts/contract_form.html", context)


@login_required
def contract_edit(request, contract_id):
    """
    Chỉnh sửa hợp đồng với kiểm soát phân quyền chặt chẽ.
    """
    contract = get_object_or_404(Contract, id=contract_id)
    user_role, _ = get_user_role_and_partner(request.user)

    if user_role == UserProfile.Role.CUSTOMER:
        raise PermissionDenied("Khách hàng không có quyền chỉnh sửa hợp đồng.")
    if user_role == UserProfile.Role.STAFF and not request.user.has_perm("contracts.change_contract"):
        raise PermissionDenied("Bạn không có quyền chỉnh sửa hợp đồng.")

    errors = {}
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        partner = request.POST.get("partner", "").strip()
        signed_date = request.POST.get("signed_date") or None
        effective_date = request.POST.get("effective_date") or None
        expiry_date = request.POST.get("expiry_date") or None
        value_raw = request.POST.get("value", "0").replace(",", "").strip()
        status = request.POST.get("status", contract.status)
        description = request.POST.get("description", "").strip()

        if not name:
            errors["name"] = "Vui lòng nhập tên hợp đồng."
        if not partner:
            errors["partner"] = "Vui lòng nhập tên đối tác."

        try:
            value = Decimal(value_raw)
            if value < 0:
                errors["value"] = "Giá trị hợp đồng không thể âm."
        except Exception:
            errors["value"] = "Giá trị không hợp lệ."
            value = contract.value

        if not errors:
            contract.name = name
            contract.partner = partner
            contract.signed_date = signed_date
            contract.effective_date = effective_date
            contract.expiry_date = expiry_date
            contract.value = value
            contract.status = status
            contract.description = description
            contract.save()

            messages.success(request, f"Hợp đồng {contract.code} đã được cập nhật thành công.")
            return redirect("contract_detail", contract_id=contract.id)

    context = {
        "contract": contract,
        "status_choices": Contract.Status.choices,
        "errors": errors,
        "is_edit": True,
    }
    return render(request, "contracts/contract_form.html", context)


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """
    Đánh dấu một thông báo là đã đọc.
    """
    notif = get_object_or_404(Notification, id=notification_id)
    user_role, partner_name = get_user_role_and_partner(request.user)

    # Khách hàng chỉ được đánh dấu thông báo thuộc về đối tác của mình
    if user_role == UserProfile.Role.CUSTOMER:
        if notif.contract and notif.contract.partner != partner_name and notif.user != request.user:
            return HttpResponseForbidden("Không có quyền thao tác trên thông báo này.")

    notif.is_read = True
    notif.save(update_fields=["is_read"])

    # Tính lại số thông báo chưa đọc
    if user_role == UserProfile.Role.CUSTOMER:
        unread = Notification.objects.filter(
            Q(contract__partner=partner_name) | Q(user=request.user),
            is_read=False,
        ).count()
    else:
        unread = Notification.objects.filter(
            Q(user=request.user) | Q(user__isnull=True),
            is_read=False,
        ).count()

    return JsonResponse({"success": True, "notification_id": notif.id, "unread_count": unread})


@login_required
@require_POST
def mark_all_notifications_read(request):
    """
    Đánh dấu tất cả thông báo của người dùng là đã đọc.
    """
    user_role, partner_name = get_user_role_and_partner(request.user)
    if user_role == UserProfile.Role.CUSTOMER:
        Notification.objects.filter(
            Q(contract__partner=partner_name) | Q(user=request.user),
            is_read=False,
        ).update(is_read=True)
    else:
        Notification.objects.filter(
            Q(user=request.user) | Q(user__isnull=True),
            is_read=False,
        ).update(is_read=True)

    return JsonResponse({"success": True, "unread_count": 0})
