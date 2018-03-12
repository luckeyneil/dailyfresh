from django.core.urlresolvers import reverse
from django.http import JsonResponse
from django.shortcuts import render, redirect

# Create your views here.
from django.views.generic import View
from django_redis import get_redis_connection

from goods.models import GoodsSKU


class AddCartView(View):
    """
    添加购物车内容的视图，为post请求
    """

    def post(self, request):
        """
        添加购物车内容，是post请求
        1.通过request获取user, sku_id, count
        2.认证系统判读是否登录
        3.all()判断是否为空
        4.判断数值是否符合仓库内容
            4.1 判断sku_id是否存在
            4.2 判断count是否超出库存
            4.3 count应该不需要判断是否为整吧？？毕竟传不进来

        5.保存到redis
            5.1 先获取此商品id对应的值 hget()
            5.2 判断值是否为None，若不为None，则把当前count加上去
            5.3 保存 hset()

        6.从redis获取购物车商品总数，并用json返回
            6.1 hgetall()

        7.注意几个获取的数据都需要str转int

        :param request: 请求对象
        :return: 返回json数据
        """
        # 1.
        # 通过request获取user, sku_id, count
        user = request.user
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('num_show')

        # 2.
        # 认证系统判读是否登录
        if not user.is_authenticated():
            print('未登录，跳转到登录页面')
            return redirect(reverse('users:login'))

        user_id = user.get('id')
        print('user_id=',user_id)
        user_id = user.id
        print('user_id=',user_id)

        # 3.
        # all() 判断是否为空
        if not all((sku_id, count)):
            return JsonResponse({'code':1, 'msg':'请求数据为空'})

        # 4.
        # 判断数值是否符合仓库内容

        # 4.1
        # 判断sku_id是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            print('sku不存在')
            return JsonResponse({'code':2, 'msg':'请求的sku不存在'})

        # 4.2
        # 判断count是否超出库存
        # stock = sku.get('stock')
        stock = sku.stock
        print(stock)
        if count > int(stock):
            print('超出库存')
            return JsonResponse({'code':3, 'msg':'超出库存'})

        # 4.3
        # count应该不需要判断是否为整吧？？毕竟传不进来

        # 5.
        # 保存到redis   cart_user_id : sku_id1 count1 sku_id2 count2....

        redis_conn = get_redis_connection('default')
        # 5.1
        # 先获取此商品id对应的值
        # hget()
        ret_num = redis_conn.hget(user_id, sku_id)
        print('ret_num=',ret_num)

        # 5.2
        # 判断值是否为None，若不为None，则把当前count加上去
        if not ret_num:
            ret_num = 0
        count += int(ret_num)

        # 5.3
        # 保存
        # hset()
        redis_conn.hset(user_id, sku_id)

        # 6.
        # 从redis获取购物车商品总数，并用json返回
        # 6.1
        # hgetall()
        cart_num = 0
        cart_dict = redis_conn.hgetall('cart_%s'%user_id)

        for val in cart_dict.values():
            cart_num += int(val)

        return JsonResponse({'code':0, 'cart_num':cart_num})

