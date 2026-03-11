import random
import string
from django.core.mail import send_mail
from django.conf import settings


def generate_code(length=6):
    return ''.join(random.choices(string.digits, k=length))


def send_verification_email(customer, code):
    send_mail(
        subject='Código de verificación — Backyard Bar',
        message=(
            f'Hola {customer.user.first_name}!\n\n'
            f'Tu código de verificación es: {code}\n\n'
            f'El código expira en 15 minutos.\n\n'
            f'Si no solicitaste este código, ignorá este mensaje.'
        ),
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@backyardbar.fun'),
        recipient_list=[customer.user.email],
        fail_silently=False,
    )


def send_verification_sms(customer, code):
    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
    from_number = getattr(settings, 'TWILIO_PHONE_NUMBER', None)

    if not all([account_sid, auth_token, from_number]):
        raise ValueError('Twilio no está configurado. Configurá TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN y TWILIO_PHONE_NUMBER en settings.')

    from twilio.rest import Client
    client = Client(account_sid, auth_token)
    client.messages.create(
        body=f'Backyard Bar: tu código es {code}. Expira en 15 minutos.',
        from_=from_number,
        to=customer.phone,
    )
