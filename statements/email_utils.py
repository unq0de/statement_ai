from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string


def send_case_email(template_name, context, recipient):
    template_path = f'emails/{template_name}'
    subject = render_to_string(f'{template_path}_subject.txt', context).strip()
    text_body = render_to_string(f'{template_path}.txt', context)

    if not settings.EMAIL_USE_HTML_TEMPLATES:
        return send_mail(
            subject=subject,
            message=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    html_body = render_to_string(f'{template_path}.html', context)
    message.attach_alternative(html_body, 'text/html')
    return message.send(fail_silently=False)