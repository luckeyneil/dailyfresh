import re

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.sessions.backends import db
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import View

from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, SignatureExpired
from celerytasks.tasks import send_active_email
from users.models import User, Address

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
from utils.views import LoginRequiredMinix


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
        # return HttpResponse('注册逻辑实现')

        token = user.generate_active_token()
        # subject = "天天生鲜用户激活"  # 标题
        message = ""  # 文本邮件体
        # from_email = settings.EMAIL_FROM  # 发件人
        recipient_list = ['luckey_one@163.com']  # 接收人
        # html_body = '<h1>尊敬的用户 %s, 感谢您注册天天生鲜！</h1>' \
        #             '<br/><p>请点击此链接激活您的帐号<a href="http://127.0.0.1:8000/users/active/%s">' \
        #             'http://127.0.0.1:8000/users/active/%s</a></p>' % (username, token, token)
        # send_mail如何使用？？？？？？？？？
        # send_mail(subject, message, from_email, recipient_list,
        #       fail_silently=False, auth_user=None, auth_password=None,
        #       connection=None, html_message=html_body)

        # 发送邮件的方法  发邮件是耗时的  处理图片 音视频 需要异步执行
        # 通过delay调用 通知work执行任务
        send_active_email.delay(recipient_list, user.username, token)

        return HttpResponse('发动激活邮件实现')


class ActiveView(View):
    """激活逻辑"""

    def get(self, request, token):
        # 生成序列化器,默认过期时间就是3600秒，可不写
        s = Serializer(secret_key=settings.SECRET_KEY)

        # 1.获取token值的明文,用loads，注意，不是load
        try:
            result = s.loads(token)
            print(result)  # 转码的字典明文

            # Exception Type: SignatureExpired
            # 1.1 注意捕获token过期异常
        except SignatureExpired:
            return HttpResponse('激活链接已过期')

        # 2.获取明文中的键‘confirm’对应的值user_id
        user_id = result.get('confirm')

        # 3.通过user_id 获取对应id的用户
        try:
            user = User.objects.get(id=user_id)
            # 3.1 注意捕获用户id不存在的异常
        except User.DoesNotExist:
            return HttpResponse('用户id不存在')
        # 4.激活用户并保存
        user.is_active = True
        user.save()

        # 5.重定向到登录界面
        # return redirect()
        return HttpResponse('这里重定向到登录界面')


class LoginView(View):
    """登录视图"""

    def get(self, request):

        return render(request, 'login.html')

    def post(self, request):
        """
        # 1.获取输入的用户名密码   request.POST.get()

        # 2.验证用户名密码是否为空   all()

        # 3.验证是否登录成功
            # 3.1 认证系统函数获取此用户名和密码的用户对象   authenticate(用户名，密码)
                # 3.1.1 判断此用户是否存在   user is None
            # 3.2 判断此用户对象是否激活    user.is_activate == False
            # 3.3 登录状态存入session     login(request, user)
        :param request:
        :return:
        """
        # 0.初始化，先登出
        logout(request)

        # 1.获取输入的用户名密码
        username = request.POST.get('username')
        pwd = request.POST.get('pwd')

        # 2.验证用户名密码是否为空   all()
        if not all([username, pwd]):
            return redirect(reverse('users:login'))

        # print(222)
        # 3.验证是否登录成功
        # 3.1 认证系统函数获取此用户名和密码的用户对象    authenticate(用户名，密码)
        user = authenticate(username=username, password=pwd)

        # 3.1.1 判断此用户是否存在   user is None
        if user is None:
            # return redirect(reverse('users:login'))
            # print('1111')
            return render(request, 'login.html', {'errmsg': '用户名或密码错误'})

        # 3.2 判断此用户对象是否激活   user.is_activate == False
        if user.is_active is False:
            return render(request, 'login.html', {'errmsg': '用户未激活'})

        # 3.3 登录状态存入session     login(request, user)
        login(request, user)

        # 4.状态保持
        rem = request.POST.get('rememberd')

        if rem == 'on':
            request.session.set_expiry(None)
        else:
            request.session.set_expiry(0)

        # 重定向到之前打开页面或主页
        # return HttpResponse('登录成功')
        next_url = request.GET.get('next')
        print(next_url)  # 当没有get时，返回None
        if next_url:
            return redirect(next_url)
        else:
            return redirect(reverse('goods:index'))


class LogoutView(View):
    """登出逻辑"""

    def get(self, request):
        logout(request)
        return redirect(reverse('goods:index'))


class AddressView(LoginRequiredMinix, View):
    """用户地址"""

    def get(self, request):
        """提供用户地址的页面"""
        # 从request中获取user对象，中间件从验证请求中的用户，所以request中带有user
        user = request.user

        try:
            # 查询用户地址：根据创建时间排序，取第1个地址
            # address = Address.objects.filter(user=user).order_by('create_time')[0]
            # address = user.address_set.order_by('create_time')[0]
            print(111)
            address = user.address_set.latest('create_time')
            print('address=', address)
            # address=address.objects.get('detail_addr')
            # print('address=', address)

        except Address.DoesNotExist:
            # 如果地址信息不存在
            address = None

        # 构造上下文
        context = {
            # 'user':user, # request中自带user,调用模板时，request会传给模板
            'address': address
        }

        # return HttpResponse('这是用户中心地址页面')
        return render(request, 'user_center_site.html', context)

    def post(self, request):
        """修改地址信息"""
        # 接收地址表单数据
        user = request.user
        recv_name = request.POST.get("recv_name")
        addr = request.POST.get("addr")
        zip_code = request.POST.get("zip_code")
        recv_mobile = request.POST.get("recv_mobile")
        print([recv_name, addr, zip_code, recv_mobile])
        # 参数校验
        if all([recv_name, addr, zip_code, recv_mobile]):
            # address = Address(
            #     user=user,
            #     receiver_name=recv_name,
            #     detail_addr=addr,
            #     zip_code=zip_code,
            #     receiver_mobile=recv_mobile
            # )
            # address.save()

            # 保存地址信息到数据库
            ret = Address.objects.create(
                user=user,
                receiver_name=recv_name,
                detail_addr=addr,
                zip_code=zip_code,
                receiver_mobile=recv_mobile
            )

            print(ret)
            print('保存成功')

        return redirect(reverse("users:address"))


class InfoView(LoginRequiredMinix, View):
    """用户信息"""

    def get(self, request):
        """提供用户信息的页面"""
        return render(request, 'user_center_info.html')

    def post(self, request):
        """修改地址信息"""
        pass


class OrderView(LoginRequiredMinix, View):
    """用户订单"""

    def get(self, request):
        """提供用户订单的页面"""
        return render(request, 'user_center_order.html')

    def post(self, request):
        """修改地址信息"""
        pass
