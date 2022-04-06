"""
1.生产者--任务函数
2.这个函数必须要让celery实例的task装饰器来装饰
3.需要celery自动检测指定包的任务
"""

from django.core.mail import send_mail
from celery_tasks.main import app


@app.task
def celery_send_email(subject, message, from_email, recipient_list, html_message):
    send_mail(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=recipient_list,
        html_message=html_message,
    )
