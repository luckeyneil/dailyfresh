import re

from django.contrib.sessions.backends import db
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import View

from users.models import User


# Create your views here.


# def register(request):
#
#     # 同时处理get和post请求
#
#     print(request.method)
#     if request.method == 'GET':
#
#         return render(request, 'register.html')
#
#     else:
#
#         return HttpResponse('处理post请求')


# 类视图
# from djcelery import db


class RegisterView(View):
    def get(self, request):

        return render(request, 'register.html')

    def post(self, request):
        """
        实现注册请求：
        1.判断是否所有文本都有填字
            1.1 用all（）函数判断是否有填字

        2.分别正则判断各字段是否符合规则
            2.1 正则匹配用户名
            2.2 正则匹配密码
            2.3 正则匹配邮箱
            2.4 判断勾选框是否勾选

        3.保存注册信息到数据库
            3.1 为了给密码加密，用django自带的方法create_user，并将默认激活的状态改为未激活，并保存！

        4.激活用户
            4.1 异步操作
            4.2 生成token
            4.3 发送到用户邮箱，由用户点击后链接到我们的激活页面，附带了token值，从而进行激活

        :param request:
        :return:
        """
        username = request.POST.get('user_name')
        pwd = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        if allow != 'on':
            errallow = True
        else:
            errallow = False

        # context = {'username':username, 'email':email}
        # print('------------1')
        # 参数校验，如果有一个为布尔False，则直接返回
        if not all((username, pwd, email)):  # all((x1,x2,x3,,,)),x1x2x3中只要有一个为False，结果就为False
            return redirect(reverse('users:register'))  # 反向解析重定向

        # print('------------2')
        # 判断邮箱
        if not re.match(r"^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$", email):
            return render(request, 'register.html',
                          {'username': username, 'email': email, 'errallow': errallow, 'err': '邮箱格式不正确'})
        #
        # print('------------3')
        # 判断是否勾选协议
        if allow != 'on':
            return render(request, 'register.html',
                          {'username': username, 'email': email, 'errallow': errallow, 'err': '没有勾选用户协议'})

        # 保存数据到数据库
        try:
            # 隐私信息需要加密，可以直接使用django提供的用户认证系统完成
            user = User.objects.create_user(username, email=email, password=pwd)
        except db.IntegrityError:
            return render(request, 'register.html', {'err': '用户已注册'})

        # 手动的将用户认证系统默认的激活状态is_active设置成False,默认是True
        user.is_active = False
        # 保存数据到数据库
        user.save()

        return HttpResponse('注册逻辑实现')


class ActiveView(View):
    """激活逻辑"""
    def get(self, request):
        pass
        # return render(request, '')