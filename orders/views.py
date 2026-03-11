import json
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from menu.models import Category, MenuItem, SiteConfig

from .forms import LoginForm, RegisterForm, VerifyForm
from .models import Customer, Order, OrderItem, VerificationCode
from .utils import generate_code, send_verification_email, send_verification_sms


# ── Helpers ──────────────────────────────────────────────────

def _get_customer(user):
    try:
        return user.customer
    except Customer.DoesNotExist:
        return None


def _create_and_send_code(customer, method):
    code = generate_code()
    code_obj = VerificationCode.objects.create(customer=customer, code=code, method=method)
    try:
        if method == 'sms':
            send_verification_sms(customer, code)
        else:
            send_verification_email(customer, code)
    except Exception:
        pass  # Code created, user can resend
    return code_obj


def _staff_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return redirect('orders:login')
        return view_func(request, *args, **kwargs)
    return wrapper


def _customer_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('orders:login')
        customer = _get_customer(request.user)
        if not customer:
            return redirect('orders:register')
        if not customer.is_verified:
            return redirect('orders:verify')
        return view_func(request, *args, **kwargs)
    return wrapper


# ── Public views ─────────────────────────────────────────────

def orders_home(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('orders:panel_orders')
        customer = _get_customer(request.user)
        if customer and customer.is_verified:
            return redirect('orders:menu')
        elif customer:
            return redirect('orders:verify')
        return redirect('orders:register')
    return redirect('orders:login')


def register_view(request):
    if request.user.is_authenticated and _get_customer(request.user):
        return redirect('orders:home')

    config = SiteConfig.get_config()
    sms_enabled = bool(getattr(settings, 'TWILIO_ACCOUNT_SID', None))

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            user = User.objects.create_user(
                username=d['email'].lower(),
                email=d['email'].lower(),
                password=d['password'],
                first_name=d['first_name'],
                last_name=d['last_name'],
            )
            customer = Customer.objects.create(
                user=user,
                phone=d['phone'],
                address=d['address'],
                street_number=d['street_number'],
                corner=d.get('corner', ''),
            )
            method = d['verification_method']
            if method == 'sms' and not sms_enabled:
                method = 'email'

            _create_and_send_code(customer, method)
            login(request, user)
            request.session['verification_method'] = method
            messages.success(request, f'Cuenta creada. Ingresá el código enviado a tu {method}.')
            return redirect('orders:verify')
    else:
        form = RegisterForm()

    return render(request, 'orders/register.html', {
        'form': form, 'config': config, 'sms_enabled': sms_enabled,
    })


def verify_view(request):
    if not request.user.is_authenticated:
        return redirect('orders:login')

    customer = _get_customer(request.user)
    if not customer:
        return redirect('orders:register')
    if customer.is_verified:
        return redirect('orders:menu')

    config = SiteConfig.get_config()
    method = request.session.get('verification_method', 'email')

    if request.method == 'POST':
        if 'resend' in request.POST:
            _create_and_send_code(customer, method)
            messages.info(request, 'Se reenvió el código.')
            return redirect('orders:verify')

        form = VerifyForm(request.POST)
        if form.is_valid():
            code_input = form.cleaned_data['code'].strip()
            code_obj = (
                VerificationCode.objects
                .filter(customer=customer, is_used=False)
                .order_by('-created_at')
                .first()
            )
            if code_obj and code_obj.is_valid and code_obj.code == code_input:
                code_obj.is_used = True
                code_obj.save()
                customer.is_verified = True
                customer.save()
                messages.success(request, '¡Cuenta verificada! Ya podés hacer pedidos.')
                return redirect('orders:menu')
            else:
                form.add_error('code', 'Código incorrecto o expirado.')
    else:
        form = VerifyForm()

    return render(request, 'orders/verify.html', {
        'form': form, 'config': config, 'method': method,
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect('orders:home')

    config = SiteConfig.get_config()

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            user = authenticate(request, username=d['email'].lower(), password=d['password'])
            if user:
                login(request, user)
                next_url = request.GET.get('next', '')
                if next_url:
                    return redirect(next_url)
                return redirect('orders:home')
            else:
                form.add_error(None, 'Email o contraseña incorrectos.')
    else:
        form = LoginForm()

    return render(request, 'orders/login.html', {'form': form, 'config': config})


def logout_view(request):
    logout(request)
    return redirect('orders:login')


# ── Customer views ───────────────────────────────────────────

@_customer_required
def menu_view(request):
    customer = request.user.customer
    config = SiteConfig.get_config()
    categories = (
        Category.objects
        .filter(is_active=True)
        .prefetch_related('menuitem_set')
        .order_by('order')
    )
    featured = MenuItem.objects.filter(is_featured=True, is_available=True).order_by('order')

    active_order = (
        customer.orders
        .filter(status__in=[Order.STATUS_IN_PROCESS, Order.STATUS_OUT_FOR_DELIVERY])
        .order_by('-created_at')
        .first()
    )

    return render(request, 'orders/menu.html', {
        'config': config,
        'categories': categories,
        'featured': featured,
        'customer': customer,
        'active_order': active_order,
    })


@_customer_required
@require_POST
def place_order(request):
    customer = request.user.customer
    try:
        data = json.loads(request.body)
        items = data.get('items', [])
        notes = data.get('notes', '').strip()

        if not items:
            return JsonResponse({'error': 'El carrito está vacío.'}, status=400)

        order = Order.objects.create(
            customer=customer,
            notes=notes,
            status=Order.STATUS_IN_PROCESS,
        )

        for item_data in items:
            menu_item = get_object_or_404(MenuItem, pk=item_data['id'], is_available=True)
            qty = max(1, int(item_data.get('quantity', 1)))
            OrderItem.objects.create(
                order=order,
                menu_item=menu_item,
                quantity=qty,
                unit_price=menu_item.price,
            )

        order.recalculate_total()

        return JsonResponse({'order_id': order.pk})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@_customer_required
def order_status_view(request, order_id):
    customer = request.user.customer
    order = get_object_or_404(Order, pk=order_id, customer=customer)
    config = SiteConfig.get_config()
    return render(request, 'orders/order_status.html', {
        'order': order,
        'config': config,
        'customer': customer,
    })


@_customer_required
def order_status_api(request, order_id):
    customer = request.user.customer
    order = get_object_or_404(Order, pk=order_id, customer=customer)
    return JsonResponse({
        'status': order.status,
        'status_display': order.get_status_display(),
    })


# ── Staff panel ──────────────────────────────────────────────

@_staff_required
def panel_orders(request):
    status_filter = request.GET.get('status', '')
    qs = Order.objects.select_related('customer__user').prefetch_related('items__menu_item')
    if status_filter:
        qs = qs.filter(status=status_filter)
    qs = qs.order_by('-created_at')

    pending_count = Order.objects.filter(status=Order.STATUS_IN_PROCESS).count()
    config = SiteConfig.get_config()

    return render(request, 'orders/panel/orders_list.html', {
        'orders': qs,
        'config': config,
        'status_filter': status_filter,
        'STATUS_CHOICES': Order.STATUS_CHOICES,
        'pending_count': pending_count,
    })


@_staff_required
def panel_order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related('customer__user').prefetch_related('items__menu_item'),
        pk=order_id,
    )
    config = SiteConfig.get_config()
    return render(request, 'orders/panel/order_detail.html', {
        'order': order,
        'config': config,
        'STATUS_CHOICES': Order.STATUS_CHOICES,
    })


@_staff_required
@require_POST
def panel_update_status(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    new_status = request.POST.get('status')
    valid = [s[0] for s in Order.STATUS_CHOICES]
    if new_status in valid:
        order.status = new_status
        order.save(update_fields=['status', 'updated_at'])

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': order.status,
            'status_display': order.get_status_display(),
        })
    return redirect('orders:panel_order_detail', order_id=order_id)
