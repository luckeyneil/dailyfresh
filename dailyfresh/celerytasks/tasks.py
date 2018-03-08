import os

os.environ["DJANGO_SETTINGS_MODULE"] = "dailyfresh.settings"
# 放到Celery服务器上时添加的代码
import django

django.setup()

from celery import Celery
from django.core.mail import send_mail
from django.conf import settings

# 创建celery应用对象
app = Celery(main='celerytasks.tasks', broker='redis://127.0.0.1:6379/6')
# Celery()


@app.task   # send_active_email = app.task(send_active_email)
def send_active_email(recipient_list, username, token):
    """发送激活邮件"""

    subject = "天天生鲜用户激活"  # 标题
    body = ""  # 文本邮件体
    sender = settings.EMAIL_FROM  # 发件人
    recipient_list = recipient_list  # 接收人
    html_body = '<h1>尊敬的用户 %s, 感谢您注册天天生鲜！</h1>' \
                '<br/><p>请点击此链接激活您的帐号<a href="http://127.0.0.1:8000/users/active/%s">' \
                'http://127.0.0.1:8000/users/active/%s</a></p>' % (username, token, token)
    send_mail(subject, body, sender, recipient_list, html_message=html_body)
