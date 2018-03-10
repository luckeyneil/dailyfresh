# vim tasks.py
#!/usr/bin/env python
# File: task.py
#

import os

os.environ["DJANGO_SETTINGS_MODULE"] = "dailyfresh.settings"
# # 放到Celery服务器上时添加的代码
# import django
# django.setup()

################################################################

from celery import Celery
from django.core.mail import send_mail
from django.conf import settings
from django.template import loader

from goods.models import *

# 创建celery应用对象
app = Celery('celerytasks.tasks', broker='redis://127.0.0.1:6379/6')

# Celery()

#app.conf.CELERY_TASK_SERIALIZER='json'
# app.conf.CELERY_ACCEPT_CONTENT=['json']
# app.conf.update(
#     CELERY_TASK_SERIALIZER='json',
#     CELERY_ACCEPT_CONTENT=['json'],
#     CELERY_RESULT_SERIALIZER='json',
#     )

@app.task  # send_active_email = app.task(send_active_email)
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


@app.task
def generate_static_index_html():
    """
    生成静态主页并写入index.html文件中
    :return:
    """
    # 获取商品分类信息查询集
    categorys = GoodsCategory.objects.all()

    # 获取轮播图查询集
    banners = IndexGoodsBanner.objects.all().order_by('index')

    # 获取广告图查询集
    promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

    # 获取分类详情商品查询集 <保存到商品分类对象中>
    for category in categorys:
        # category是一类商品类
        # 标题类商品
        title_goods = IndexCategoryGoodsBanner.objects.filter(category=category, display_type=0).order_by('index')
        category.title_goods = title_goods
        # 图片类商品
        picture_goods = IndexCategoryGoodsBanner.objects.filter(category=category, display_type=1).order_by('index')
        category.picture_goods = picture_goods

    # 获取购物车计数
    cart_num = 0

    context = {
        'categorys': categorys,  # 获取商品分类信息查询集,查询集内元素含有分类详情商品查询集
        'banners': banners,  # 获取轮播图查询集
        'promotion_banners': promotion_banners,  # 获取广告图查询集
        'cart_num': cart_num  # 获取购物车计数
    }

    # 生成静态页面数据
    # # 加载模板,  这一步是怎么找到静态模板文件的？？？？？
    # template = loader.get_template('static_index.html')
    # # 模板调用render，生成静态页面数据
    # html_data = template.render(context)

    html_data = loader.render_to_string('static_index.html', context)

    # 写入index.html文件
    file_path = os.path.join(settings.STATICFILES_DIRS[0], 'index.html')
    with open(file_path, 'w') as f:
        f.write(html_data)
