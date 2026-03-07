from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Category, MenuItem, Table, SiteConfig
from .forms import CategoryForm, MenuItemForm, TableForm, SiteConfigForm


# ─────────────────────────────────────────
#  MENU PÚBLICO
# ─────────────────────────────────────────

def menu_view(request, table_number=None):
    config = SiteConfig.get_config()
    categories = Category.objects.filter(is_active=True).prefetch_related('items')
    featured = MenuItem.objects.filter(is_available=True, is_featured=True).select_related('category')
    table = None
    if table_number:
        table = get_object_or_404(Table, number=table_number, is_active=True)
    return render(request, 'menu/menu.html', {
        'config': config,
        'categories': categories,
        'featured': featured,
        'table': table,
    })


def menu_category(request, category_id, table_number=None):
    config = SiteConfig.get_config()
    category = get_object_or_404(Category, pk=category_id, is_active=True)
    categories = Category.objects.filter(is_active=True)
    table = None
    if table_number:
        table = get_object_or_404(Table, number=table_number, is_active=True)
    return render(request, 'menu/menu.html', {
        'config': config,
        'categories': categories,
        'active_category': category,
        'items': category.items.filter(is_available=True),
        'table': table,
    })


# ─────────────────────────────────────────
#  AUTH
# ─────────────────────────────────────────

def panel_login(request):
    if request.user.is_authenticated:
        return redirect('menu:panel_dashboard')
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password'),
        )
        if user and user.is_staff:
            login(request, user)
            return redirect('menu:panel_dashboard')
        messages.error(request, 'Usuario o contraseña incorrectos.')
    return render(request, 'menu/panel/login.html', {'config': SiteConfig.get_config()})


def panel_logout(request):
    logout(request)
    return redirect('menu:panel_login')


# ─────────────────────────────────────────
#  PANEL - DASHBOARD
# ─────────────────────────────────────────

@login_required
def panel_dashboard(request):
    return render(request, 'menu/panel/dashboard.html', {
        'config': SiteConfig.get_config(),
        'total_categories': Category.objects.count(),
        'total_items': MenuItem.objects.count(),
        'available_items': MenuItem.objects.filter(is_available=True).count(),
        'total_tables': Table.objects.count(),
        'featured_items': MenuItem.objects.filter(is_featured=True).count(),
    })


# ─────────────────────────────────────────
#  PANEL - CATEGORÍAS
# ─────────────────────────────────────────

@login_required
def panel_categories(request):
    return render(request, 'menu/panel/categories.html', {
        'config': SiteConfig.get_config(),
        'categories': Category.objects.all(),
    })


@login_required
def panel_category_form(request, pk=None):
    instance = get_object_or_404(Category, pk=pk) if pk else None
    form = CategoryForm(request.POST or None, instance=instance)
    if form.is_valid():
        form.save()
        messages.success(request, f'Categoría {"actualizada" if pk else "creada"} correctamente.')
        return redirect('menu:panel_categories')
    return render(request, 'menu/panel/category_form.html', {
        'config': SiteConfig.get_config(),
        'form': form,
        'instance': instance,
    })


@login_required
def panel_category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Categoría eliminada.')
        return redirect('menu:panel_categories')
    return render(request, 'menu/panel/confirm_delete.html', {
        'config': SiteConfig.get_config(),
        'object': category,
        'back_url': 'menu:panel_categories',
    })


# ─────────────────────────────────────────
#  PANEL - ITEMS
# ─────────────────────────────────────────

@login_required
def panel_items(request):
    category_id = request.GET.get('categoria')
    items = MenuItem.objects.select_related('category').all()
    if category_id:
        items = items.filter(category_id=category_id)
    return render(request, 'menu/panel/items.html', {
        'config': SiteConfig.get_config(),
        'items': items,
        'categories': Category.objects.all(),
        'active_category_id': int(category_id) if category_id else None,
    })


@login_required
def panel_item_form(request, pk=None):
    instance = get_object_or_404(MenuItem, pk=pk) if pk else None
    form = MenuItemForm(request.POST or None, request.FILES or None, instance=instance)
    if form.is_valid():
        form.save()
        messages.success(request, f'Item {"actualizado" if pk else "creado"} correctamente.')
        return redirect('menu:panel_items')
    return render(request, 'menu/panel/item_form.html', {
        'config': SiteConfig.get_config(),
        'form': form,
        'instance': instance,
    })


@login_required
def panel_item_delete(request, pk):
    item = get_object_or_404(MenuItem, pk=pk)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Item eliminado.')
        return redirect('menu:panel_items')
    return render(request, 'menu/panel/confirm_delete.html', {
        'config': SiteConfig.get_config(),
        'object': item,
        'back_url': 'menu:panel_items',
    })


# ─────────────────────────────────────────
#  PANEL - MESAS y QR
# ─────────────────────────────────────────

@login_required
def panel_tables(request):
    config = SiteConfig.get_config()
    if request.method == 'POST':
        base_url = request.POST.get('base_url', config.base_url).rstrip('/')
        config.base_url = base_url
        config.save()
        for table in Table.objects.filter(is_active=True):
            table.generate_qr(base_url)
        messages.success(request, 'QR regenerados para todas las mesas activas.')
        return redirect('menu:panel_tables')
    return render(request, 'menu/panel/tables.html', {
        'config': config,
        'tables': Table.objects.all(),
    })


@login_required
def panel_table_form(request, pk=None):
    instance = get_object_or_404(Table, pk=pk) if pk else None
    form = TableForm(request.POST or None, instance=instance)
    if form.is_valid():
        form.save()
        messages.success(request, f'Mesa {"actualizada" if pk else "creada"} correctamente.')
        return redirect('menu:panel_tables')
    return render(request, 'menu/panel/table_form.html', {
        'config': SiteConfig.get_config(),
        'form': form,
        'instance': instance,
    })


@login_required
def panel_table_delete(request, pk):
    table = get_object_or_404(Table, pk=pk)
    if request.method == 'POST':
        table.delete()
        messages.success(request, 'Mesa eliminada.')
        return redirect('menu:panel_tables')
    return render(request, 'menu/panel/confirm_delete.html', {
        'config': SiteConfig.get_config(),
        'object': table,
        'back_url': 'menu:panel_tables',
    })


@login_required
def panel_generate_qr(request, pk):
    table = get_object_or_404(Table, pk=pk)
    config = SiteConfig.get_config()
    table.generate_qr(config.base_url.rstrip('/'))
    messages.success(request, f'QR generado para {table}.')
    return redirect('menu:panel_tables')


# ─────────────────────────────────────────
#  PANEL - CONFIGURACIÓN
# ─────────────────────────────────────────

@login_required
def panel_config(request):
    config = SiteConfig.get_config()
    form = SiteConfigForm(request.POST or None, request.FILES or None, instance=config)
    if form.is_valid():
        form.save()
        messages.success(request, 'Configuración guardada.')
        return redirect('menu:panel_config')
    return render(request, 'menu/panel/config.html', {
        'config': config,
        'form': form,
    })
