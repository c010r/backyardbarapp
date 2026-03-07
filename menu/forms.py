from django import forms
from .models import Category, MenuItem, Table, SiteConfig


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'icon', 'order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: Cervezas'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Descripción opcional'}),
            'icon': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '🍺'}),
            'order': forms.NumberInput(attrs={'class': 'form-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class MenuItemForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = ['category', 'name', 'description', 'price', 'image',
                  'is_available', 'is_featured', 'order', 'tags']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-input'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: IPA artesanal'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'price': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-input-file'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'order': forms.NumberInput(attrs={'class': 'form-input'}),
            'tags': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'vegano, sin gluten, picante'}),
        }


class TableForm(forms.ModelForm):
    class Meta:
        model = Table
        fields = ['number', 'name', 'is_active']
        widgets = {
            'number': forms.NumberInput(attrs={'class': 'form-input', 'min': '1'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: Terraza, VIP (opcional)'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class SiteConfigForm(forms.ModelForm):
    class Meta:
        model = SiteConfig
        fields = ['bar_name', 'tagline', 'logo', 'base_url',
                  'primary_color', 'secondary_color', 'footer_text']
        widgets = {
            'bar_name': forms.TextInput(attrs={'class': 'form-input'}),
            'tagline': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Good vibes & great drinks'}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-input-file'}),
            'base_url': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'http://192.168.1.10:8000'}),
            'primary_color': forms.TextInput(attrs={'class': 'form-input form-color', 'type': 'color'}),
            'secondary_color': forms.TextInput(attrs={'class': 'form-input form-color', 'type': 'color'}),
            'footer_text': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
        }
