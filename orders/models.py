from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer')
    phone = models.CharField('Teléfono', max_length=30)
    address = models.CharField('Calle / Dirección', max_length=200)
    street_number = models.CharField('Número', max_length=20)
    corner = models.CharField('Esquina', max_length=100, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.first_name} {self.user.last_name} ({self.user.email})'

    @property
    def full_name(self):
        return f'{self.user.first_name} {self.user.last_name}'.strip()

    @property
    def full_address(self):
        parts = [self.address, self.street_number]
        if self.corner:
            parts.append(f'esq. {self.corner}')
        return ', '.join(parts)


class VerificationCode(models.Model):
    METHOD_CHOICES = [('email', 'Email'), ('sms', 'SMS')]
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='codes')
    code = models.CharField(max_length=6)
    method = models.CharField(max_length=5, choices=METHOD_CHOICES, default='email')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.expires_at = timezone.now() + timedelta(minutes=15)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at

    class Meta:
        verbose_name = 'Código de verificación'
        verbose_name_plural = 'Códigos de verificación'
        ordering = ['-created_at']


class Order(models.Model):
    STATUS_IN_PROCESS = 'in_process'
    STATUS_OUT_FOR_DELIVERY = 'out_for_delivery'
    STATUS_DELIVERED = 'delivered'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_IN_PROCESS, 'En proceso'),
        (STATUS_OUT_FOR_DELIVERY, 'Delivery en camino'),
        (STATUS_DELIVERED, 'Entregado'),
        (STATUS_CANCELLED, 'Cancelado'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_IN_PROCESS)
    notes = models.TextField('Notas', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-created_at']

    def __str__(self):
        return f'Pedido #{self.pk} — {self.customer} ({self.get_status_display()})'

    def recalculate_total(self):
        self.total = sum(item.subtotal for item in self.items.all())
        self.save(update_fields=['total'])


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey('menu.MenuItem', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    subtotal = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Item del pedido'
        verbose_name_plural = 'Items del pedido'

    def __str__(self):
        return f'{self.quantity}x {self.menu_item.name}'

    def save(self, *args, **kwargs):
        self.subtotal = self.unit_price * self.quantity
        super().save(*args, **kwargs)
