from django import forms
from django.contrib.auth.models import User


class RegisterForm(forms.Form):
    first_name = forms.CharField(label='Nombre', max_length=100)
    last_name = forms.CharField(label='Apellido', max_length=100)
    email = forms.EmailField(label='Email')
    phone = forms.CharField(label='Teléfono', max_length=30)
    address = forms.CharField(label='Calle / Dirección', max_length=200)
    street_number = forms.CharField(label='Número', max_length=20)
    corner = forms.CharField(label='Esquina (opcional)', max_length=100, required=False)
    password = forms.CharField(label='Contraseña', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirmar contraseña', widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con este email.')
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Las contraseñas no coinciden.')
        return cleaned


class LoginForm(forms.Form):
    email = forms.EmailField(label='Email')
    password = forms.CharField(label='Contraseña', widget=forms.PasswordInput)


class VerifyForm(forms.Form):
    code = forms.CharField(
        label='Código de verificación',
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={'placeholder': '000000', 'inputmode': 'numeric', 'autocomplete': 'one-time-code'}),
    )
