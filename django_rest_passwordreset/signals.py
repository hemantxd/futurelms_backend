import django.dispatch
from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
from notification import utils as notification_utils

reset_password_token_created = django.dispatch.Signal(
    providing_args=["reset_password_token"],
)

pre_password_reset = django.dispatch.Signal(providing_args=["user"])

post_password_reset = django.dispatch.Signal(providing_args=["user"])


@receiver(reset_password_token_created)
def password_reset_token_created(sender, reset_password_token, *args, **kwargs):
    """
    Handles password reset tokens
    When a token is created, an e-mail needs to be sent to the user
    :param sender:
    :param reset_password_token:
    :param args:
    :param kwargs:
    :return:
    """
    # send an e-mail to the user
    context = {
        'current_user': reset_password_token.user,
        'username': reset_password_token.user.username,
        'email': reset_password_token.user.email,
        'reset_password_url': "{}?token={}".format(reverse('password_reset:reset-password-request'),
                                                   reset_password_token.key),
        'token': reset_password_token.key,
    }
    try:
        # render email text
        email_html_message = render_to_string('email/user_reset_password.html', context)
        email_plaintext_message = render_to_string('email/user_reset_password.txt', context)

        msg = EmailMultiAlternatives(
            # title:
            "MAKEMYPATH App Password Reset",
            # message:
            email_plaintext_message,
            # from:
            settings.DEFAULT_FROM_EMAIL,
            # to:
            [reset_password_token.user.email]
        )
        msg.attach_alternative(email_html_message, "text/html")
        msg.send()
    except:
        pass
    try:
        message = 'Forgot Your Password?. use {} as OTP to reset your password .For any help, Contact us at +91 99588 93385. Team ERDR Academy.'.format(reset_password_token.key)
        vars_data = {("VAR1",reset_password_token.key)}
        if reset_password_token.user.phonenumber:
            notification_utils.SmsMessage(reset_password_token.user.phonenumber, 'ERDR',message, vars_data, 'aws', 'MAKEMYPATHOTP')
    except:
        pass
            
