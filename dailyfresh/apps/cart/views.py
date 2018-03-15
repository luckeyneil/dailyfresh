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
        print(111)
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


class CartInfoView(View):
    """购物车详情页面"""

    def get(self, request):
        """
        为什么是get？因为购物车详情页面不需要获取额外的数据，
        所有数据都可以从已保存的redis或cookie中获取
        1.获取sku的列表
        2.获取每种sku的数量
        3.获取每种sku的总价
        4.获取所有sku的数量
        5.获取所有sku的总价

        :param request:
        :return:
        """

        # < li class ="col01" > < input type="checkbox" name="" checked > < / li >
        # < li class ="col02" > < img src="images/goods/goods012.jpg" > < / li >
        # < li class ="col03" > 奇异果 < br > < em > 25.80元 / 500g < / em > < / li >
        # < li class ="col04" > 500g < / li >
        # < li class ="col05" > 25.80元 < / li >
        # < li class ="col06" >
        # < div class ="num_add" >
        # < a href = "javascript:;" class ="add fl" > + < / a >
        # < input type = "text" class ="num_show fl" value="1" >
        # < a href = "javascript:;" class ="minus fl" > - < / a >
        # < / div >< / li >
        # < li class ="col07" > 25.80元 < / li >
        # < li class ="col08" > < a href="javascript:;" > 删除 < / a > < / li >

        user = request.user
        # 1.获取sku对象列表 skus
        # 1.1 登不登陆两种情况获取
        if user.is_authenticated():
            # 已登录的情况
            redis_conn = get_redis_connection('default')
            cart_dict = redis_conn.hgetall('cart_%s' % user.id)  # 这是byte格式的,是cart字典
            # {b'1': b'7', b'2': b'7', b'3': b'1'}
            print(cart_dict)
            # cart_dict = cart_dict.encode()
            # print(cart_dict)
        else:
            # 未登录，从cookie中获取
            cart_json = request.COOKIES.get('cart')  # 获取的是json字符串
            print('cart_json=', cart_json)  # cart_json= {"1": 6, "3": 4}

            print(type(cart_json))
            if cart_json:
                cart_dict = json.loads(cart_json)
                # print(cart_dict)
            else:
                cart_dict = {}

        # 获取总数量 total_count
        # 获取总价格 total_amount
        skus = []
        total_count = 0
        total_amount = 0

        for sku_id, count in cart_dict.items():
            try:
                sku = GoodsSKU.objects.get(id=sku_id)
            except GoodsSKU.DoesNotExist:
                continue

            count = int(count)  # 强制转为int  每种sku的数量
            amount = sku.price * count  # 每种sku的总价

            # 添加到sku对象内
            sku.count = count
            sku.amount = amount
            # 获取总数量 total_count
            # 获取总价格 total_amount
            total_count += count
            total_amount += amount

            skus.append(sku)

        context = {
            'skus': skus,
            'total_amount': total_amount,
            'total_count': total_count
        }

        return render(request, 'cart.html', context)


class CartUpdateView(View):
    """购物车幂等性更新"""

    def post(self, request):
        """
        获取参数：sku_id, count
        校验参数all()
        判断商品是否存在
        判断count是否是整数
        判断库存
        判断用户是否登陆
        如果用户登陆，将修改的购物车数据存储到redis中
        如果用户未登陆，将修改的购物车数据存储到cookie中
        响应结果
        :param request:
        :return:
        """

        # 获取参数：sku_id, count
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        user = request.user
        # print(111)
        # try:
        # 校验参数all()
        if not all((sku_id, count)):
            return JsonResponse({'code': 1, 'message': '参数不全'})

        # 判断商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'code': 2, 'message': '商品不存在'})

        # 判断count是否是整数
        # 4.3
        # count应该不需要判断是否为整吧？？毕竟传不进来,判断是否为数字
        try:
            count = int(count)
        except Exception as e:
            print(e)
            return JsonResponse({'code': 5, 'msg': '传入数值错误'})

        # except Exception as e:
        #     print(e)

        # 4.2
        # 判断库存
        # 判断count是否超出库存
        # stock = sku.get('stock')
        stock = sku.stock
        print('stock=', stock)
        if count > int(stock):
            print('超出库存')
            return JsonResponse({'code': 4, 'msg': '超出库存'})


            # 判断用户是否登陆
            # 2.
            # 认证系统判读是否登录
        if not user.is_authenticated():
            # 未登录的情况
            # 如果用户未登陆，将修改的购物车数据存储到cookie中
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

            cart_dict[sku_id] = count

            # 4.
            # 将(cart_dict)
            # 重新生成json字符串，方便写入到cookie
            cart_json = json.dumps(cart_dict)

            # 5.
            # 创建JsonResponse对象，该对象就是要响应的对象
            response = JsonResponse({'code': 0, 'message': '请求成功'})

            # 6.
            # 在响应前，设置cookie信息
            response.set_cookie('cart', cart_json)

            return response
            # print('未登录，跳转到登录页面')
            # path = request.path
            # return JsonResponse({'code':1, 'msg':'未登录，跳转到登录页面', 'path':path})

        else:
            # 已登录的情况
            # 5.# 如果用户登陆，将修改的购物车数据存储到redis中
            # 保存到redis   cart_user_id : sku_id1 count1 sku_id2 count2....

            print(111)
            redis_conn = get_redis_connection('default')

            # 5.3
            # 保存
            # hset()
            redis_conn.hset('cart_%s' % user.id, sku_id, count)

        # 响应结果
        return JsonResponse({'code': 0, 'message': '请求成功'})



class CartDeleteView(View):
    """删除购物车商品逻辑"""

    def post(self, request):
        """
        接收参数：sku_id
        校验参数：not，判断是否为空
        判断用户是否登录
        如果用户登陆，删除redis中购物车数据
        如果用户未登陆，删除cookie中购物车数据
        :param request:
        :return:
        """

        # 接收参数：sku_id
        sku_id = request.POST.get('sku_id')
        user = request.user

        # 校验参数：not，判断是否为空
        if not sku_id:
            return JsonResponse({'code': 1, 'message': '参数不全'})

        # 判断用户是否登录
        if user.is_authenticated():
            # 如果用户登陆，删除redis中购物车数据,   hdel()
            redis_conn = get_redis_connection('default')
            redis_conn.hdel('cart_%s' % user.id, sku_id)
            response = JsonResponse({'code': 0, 'message': '删除成功'})
        else:
            # 如果用户未登陆，删除cookie中购物车数据
            cart_json = request.COOKIES.get('cart')
            if cart_json:
                cart_dict = json.loads(cart_json)
                if sku_id in cart_dict:
                    del cart_dict[sku_id]

            cart_json = json.dumps(cart_dict)

            response = JsonResponse({'code': 0, 'message': '删除成功'})
            response.set_cookie('cart', cart_json)

        return response
