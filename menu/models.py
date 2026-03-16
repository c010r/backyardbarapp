from django.db import models
from django.utils.text import slugify
import qrcode
import io
import os
from django.core.files.base import ContentFile
from django.conf import settings


class Category(models.Model):
    name = models.CharField('Nombre', max_length=100)
    description = models.TextField('Descripción', blank=True)
    icon = models.CharField('Icono (emoji)', max_length=10, blank=True, default='🍺')
    order = models.PositiveIntegerField('Orden', default=0)
    is_active = models.BooleanField('Activa', default=True)

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE,
        related_name='items', verbose_name='Categoría'
    )
    name = models.CharField('Nombre', max_length=150)
    description = models.TextField('Descripción', blank=True)
    price = models.DecimalField('Precio', max_digits=8, decimal_places=2)
    image = models.ImageField('Imagen', upload_to='menu_items/', blank=True, null=True)
    is_available = models.BooleanField('Disponible', default=True)
    is_featured = models.BooleanField('Destacado', default=False)
    order = models.PositiveIntegerField('Orden', default=0)
    tags = models.CharField(
        'Etiquetas', max_length=200, blank=True,
        help_text='Ej: vegano, sin gluten, picante (separadas por coma)'
    )

    class Meta:
        verbose_name = 'Item del menú'
        verbose_name_plural = 'Items del menú'
        ordering = ['order', 'name']

    def __str__(self):
        return f'{self.name} - ${self.price}'

    def get_tags_list(self):
        if self.tags:
            return [t.strip() for t in self.tags.split(',') if t.strip()]
        return []


class Table(models.Model):
    number = models.PositiveIntegerField('Número de mesa', unique=True)
    name = models.CharField('Nombre/Alias', max_length=50, blank=True,
                            help_text='Ej: Terraza, Barra, VIP')
    qr_code = models.ImageField('Código QR', upload_to='qr_codes/', blank=True, null=True)
    is_active = models.BooleanField('Activa', default=True)

    class Meta:
        verbose_name = 'Mesa'
        verbose_name_plural = 'Mesas'
        ordering = ['number']

    def __str__(self):
        if self.name:
            return f'Mesa {self.number} - {self.name}'
        return f'Mesa {self.number}'

    def get_display_name(self):
        return self.name if self.name else f'Mesa {self.number}'

    def generate_qr(self, base_url):
        menu_url = f'{base_url}/menu/{self.number}/'
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(menu_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='#1a1a2e', back_color='white')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        filename = f'qr_mesa_{self.number}.png'
        self.qr_code.save(filename, ContentFile(buffer.getvalue()), save=True)


class Order(models.Model):
    STATUS_NEW        = 'new'
    STATUS_PREPARING  = 'preparing'
    STATUS_READY      = 'ready'
    STATUS_DELIVERED  = 'delivered'
    STATUS_CANCELLED  = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_NEW,       '🟡 Nuevo'),
        (STATUS_PREPARING, '🔵 En preparación'),
        (STATUS_READY,     '🟢 Listo'),
        (STATUS_DELIVERED, '✅ Entregado'),
        (STATUS_CANCELLED, '❌ Cancelado'),
    ]

    table      = models.ForeignKey(Table, on_delete=models.PROTECT, related_name='orders', verbose_name='Mesa')
    status     = models.CharField('Estado', max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW)
    notes      = models.TextField('Notas del cliente', blank=True)
    created_at = models.DateTimeField('Creado', auto_now_add=True)
    updated_at = models.DateTimeField('Actualizado', auto_now=True)

    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-created_at']

    def __str__(self):
        return f'Pedido #{self.pk} — {self.table} — {self.get_status_display()}'

    def get_total(self):
        return sum(i.subtotal() for i in self.items.all())

    def get_status_color(self):
        return {
            self.STATUS_NEW:       '#f5a623',
            self.STATUS_PREPARING: '#4a9eff',
            self.STATUS_READY:     '#4caf7d',
            self.STATUS_DELIVERED: '#888',
            self.STATUS_CANCELLED: '#e05252',
        }.get(self.status, '#888')


class OrderItem(models.Model):
    order     = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT, verbose_name='Item')
    quantity  = models.PositiveIntegerField('Cantidad', default=1)
    unit_price = models.DecimalField('Precio unitario', max_digits=8, decimal_places=2)

    class Meta:
        verbose_name = 'Item del pedido'
        verbose_name_plural = 'Items del pedido'

    def __str__(self):
        return f'{self.quantity}x {self.menu_item.name}'

    def subtotal(self):
        return self.unit_price * self.quantity


class BarSale(models.Model):
    PAYMENT_CASH = 'cash'
    PAYMENT_CARD = 'card'
    PAYMENT_TRANSFER = 'transfer'
    PAYMENT_CHOICES = [
        (PAYMENT_CASH,     'Efectivo'),
        (PAYMENT_CARD,     'Tarjeta'),
        (PAYMENT_TRANSFER, 'Transferencia'),
    ]

    STATUS_PENDING   = 'pending'
    STATUS_DELIVERED = 'delivered'
    STATUS_CHOICES = [
        (STATUS_PENDING,   'Pendiente'),
        (STATUS_DELIVERED, 'Entregado'),
    ]

    ticket_number  = models.PositiveIntegerField('Nº Ticket', unique=True, editable=False)
    payment_method = models.CharField('Medio de pago', max_length=20, choices=PAYMENT_CHOICES, default=PAYMENT_CASH)
    status         = models.CharField('Estado', max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    total          = models.DecimalField('Total', max_digits=10, decimal_places=2, default=0)
    notes          = models.TextField('Notas', blank=True)
    created_at     = models.DateTimeField('Fecha', auto_now_add=True)
    created_by     = models.CharField('Cobrado por', max_length=100, blank=True)

    class Meta:
        verbose_name = 'Venta en barra'
        verbose_name_plural = 'Ventas en barra'
        ordering = ['-created_at']

    def __str__(self):
        return f'Ticket #{self.ticket_number}'

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            last = BarSale.objects.order_by('ticket_number').last()
            self.ticket_number = (last.ticket_number + 1) if last else 1
        super().save(*args, **kwargs)


class BarSaleItem(models.Model):
    sale       = models.ForeignKey(BarSale, on_delete=models.CASCADE, related_name='items')
    menu_item  = models.ForeignKey(MenuItem, on_delete=models.PROTECT, verbose_name='Producto')
    quantity   = models.PositiveIntegerField('Cantidad', default=1)
    unit_price = models.DecimalField('Precio unitario', max_digits=8, decimal_places=2)

    def subtotal(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f'{self.quantity}x {self.menu_item.name}'


class SiteConfig(models.Model):
    bar_name = models.CharField('Nombre del bar', max_length=100, default='Backyard Bar')
    tagline = models.CharField('Eslogan', max_length=200, blank=True)
    logo = models.ImageField('Logo', upload_to='site/', blank=True, null=True)
    base_url = models.CharField(
        'URL base del sitio', max_length=200, default='http://localhost:8000',
        help_text='URL que se incrustará en los códigos QR'
    )
    primary_color = models.CharField('Color primario', max_length=7, default='#f5a623')
    secondary_color = models.CharField('Color secundario', max_length=7, default='#1a1a2e')
    footer_text = models.TextField('Texto del pie', blank=True)

    class Meta:
        verbose_name = 'Configuración del sitio'
        verbose_name_plural = 'Configuración del sitio'

    def __str__(self):
        return self.bar_name

    @classmethod
    def get_config(cls):
        config, _ = cls.objects.get_or_create(pk=1)
        return config
