import json

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

        7.注意几个获取的数据都需要转码为int

        8.未登录状态添加到购物车
            8.1 通过cookie
                向浏览器中写入购物车cookie信息
                response.set_cookie('cart', cart_str)
                读取cookie中的购物车信息
                cart_json = request.COOKIES.get('cart')

        :param request: 请求对象
        :return: 返回json数据
        """
        # print(111)
        # 1.
        # 通过request获取user, sku_id, count
        user = request.user
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        user_id = user.id
        print('user_id=', user_id)

        # 3.
        # all() 判断是否为空
        if not all((sku_id, count)):
            return JsonResponse({'code': 2, 'msg': '请求数据为空'})

        # 4.
        # 判断数值是否符合仓库内容
        # 4.1
        # 判断sku_id是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            print('sku不存在')
            return JsonResponse({'code': 3, 'msg': '请求的sku不存在'})

        # 4.3
        # count应该不需要判断是否为整吧？？毕竟传不进来,判断是否为数字
        try:
            count = int(count)
        except Exception as e:
            print(e)
            return JsonResponse({'code': 5, 'msg': '传入数值错误'})

        # 4.2
        # 判断count是否超出库存
        # stock = sku.get('stock')
        stock = sku.stock
        print('stock=', stock)
        if count > int(stock):
            print('超出库存')
            return JsonResponse({'code': 4, 'msg': '超出库存'})

        # 2.
        # 认证系统判读是否登录
        if not user.is_authenticated():
            # 未登录的情况
            # 1.
            # 先从cookie中，获取当前商品的购物车记录(cart_json)

            cart_json = request.COOKIES.get('cart')

            # 2.
            # 判断购物车(cart_json)
            # 数据是否存在，有可能用户从来没有操作过购物车
            if cart_json:
                # 2.1.如果(cart_json)存在就把它转成字典(cart_dict)
                cart_dict = json.loads(cart_json)
                # cart_dict = eval(cart_json)
            else:
                # 2.2.如果(cart_json)不存在就定义空字典(cart_dict)
                cart_dict = {}

            # 3.
            # 判断要添加的商品在购物车中是否存在
            try:
                origin_count = cart_dict.get(sku_id)
                count += origin_count
            except Exception as e:
                print(e)

            # 3.1.如果存在就取出源有值，并进行累加
            # 3.2.如果不存在就直接保存商品数量
            cart_dict[sku_id] = count

            # 4.
            # 将(cart_dict)
            # 重新生成json字符串，方便写入到cookie
            cart_json = json.dumps(cart_dict)
            # cart_json = str(cart_dict)
            # 7.
            # 计算购物车数量总和，方便前端展示
            cart_num = 0
            for val in cart_dict.values():
                cart_num += val

            # 5.
            # 创建JsonResponse对象，该对象就是要响应的对象
            response = JsonResponse({'code': 0, 'msg': '添加到购物车成功', 'cart_num': cart_num})

            # 6.
            # 在响应前，设置cookie信息
            response.set_cookie('cart', cart_json)

            return response
            # print('未登录，跳转到登录页面')
            # path = request.path
            # return JsonResponse({'code':1, 'msg':'未登录，跳转到登录页面', 'path':path})

        else:
            # 已登录的情况
            # 5.
            # 保存到redis   cart_user_id : sku_id1 count1 sku_id2 count2....

            print(111)
            redis_conn = get_redis_connection('default')
            # print(222)
            # 5.1
            # 先获取此商品id对应的值
            # hget()
            ret_num = redis_conn.hget('cart_%s' % user.id, sku_id)

            print('ret_num=', ret_num)

            # 5.2
            # 判断值是否为None，若不为None，则把当前count加上去
            if not ret_num:
                ret_num = 0
            count += int(ret_num)

            print('count=', count)
            # 5.3
            # 保存
            # hset()
            redis_conn.hset('cart_%s' % user.id, sku_id, count)

            # 6.
            # 从redis获取购物车商品总数，并用json返回
            # 6.1
            # hgetall()
            cart_num = 0
            cart_dict = redis_conn.hgetall('cart_%s' % user_id)
            print(cart_dict)
            # cart_dict2 = redis_conn.hgetall('cart_11')
            # print(cart_dict2)
            # if not cart_dict:
            #     cart_dict = {}

            for val in cart_dict.values():
                cart_num += int(val)

            print('cart_num=', cart_num)

            return JsonResponse({'code': 0, 'msg': '请求成功', 'cart_num': cart_num})
