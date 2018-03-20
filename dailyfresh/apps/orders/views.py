from django.core.urlresolvers import reverse
from django.http import JsonResponse
from django.shortcuts import render, redirect

# Create your views here.
from django.views.generic import View
from django_redis import get_redis_connection

from goods.models import GoodsSKU
from orders.models import OrderInfo, OrderGoods
from users.models import Address
from utils.views import LoginRequiredMinix, LoginRequiredJSONMinix


class PlaceOrderView(LoginRequiredMinix, View):
    """订单确认页面"""

    def post(self, request):
        """
        判断用户是否登陆：LoginRequiredMixin
        获取参数：sku_ids, count
        校验sku_ids参数：not
        查询商品数据
        如果是从购物车页面过来，商品的数量从redis中获取
        如果是从详情页面过来，商品的数量从request中获取
        判断库存：详情页没有判断库存
        查询用户地址信息
        响应结果:html页面

        context = {
            'skus': skus,    # 商品sku
            'total_count': total_count,  # 总数量
            'total_sku_amount': total_sku_amount,  # 所有商品的总价
            'trans_cost': trans_cost,   # 运费
            'total_amount': total_amount,  # 实付款（含运费）
            'address': address   # 地址对象
        }

        :param request:
        :return: render
        """

        # 判断用户是否登陆：LoginRequiredMixin
        # 获取参数：sku_ids, count
        sku_ids = request.POST.getlist('sku_ids')
        # 用户从详情过来时，才有count
        count = request.POST.get('count')

        # 校验参数
        if not sku_ids:
            # 如果sku_ids没有，就重定向到购物车，重选
            return redirect(reverse('cart:info'))

        # 定义临时容器
        skus = []
        total_count = 0
        total_sku_amount = 0
        trans_cost = 10
        total_amount = 0  # 实付款

        # 查询商品数据
        if count is None:
            # 如果是从购物车页面过来，商品的数量从redis中获取
            redis_conn = get_redis_connection('default')
            user_id = request.user.id
            cart_dict = redis_conn.hgetall('cart_%s' % user_id)

            # 遍历商品sku_ids
            for sku_id in sku_ids:
                try:
                    sku = GoodsSKU.objects.get(id=sku_id)
                except GoodsSKU.DoesNotExist:
                    # 重定向到购物车
                    return redirect(reverse('cart:info'))

                # 取出每个sku_id对应的商品数量
                sku_count = cart_dict.get(sku_id.encode())
                sku_count = int(sku_count)

                # 计算商品总金额
                amount = sku.price * sku_count
                # 将商品数量和金额封装到sku对象
                sku.count = sku_count
                sku.amount = amount
                skus.append(sku)
                # 金额和数量求和
                total_count += sku_count
                total_sku_amount += amount
        else:
            # 如果是从详情页面过来，商品的数量从request中获取
            # 遍历商品sku_ids:如果是从详情过来，sku_ids只有一个sku_id
            for sku_id in sku_ids:
                try:
                    sku = GoodsSKU.objects.get(id=sku_id)
                except GoodsSKU.DoesNotExist:
                    # 重定向到购物车
                    return redirect(reverse('cart:info'))

                # 获取request中得到的count
                try:
                    sku_count = int(count)
                except Exception:
                    return redirect(reverse('goods:detail', kwargs={'sku_id': sku_id}))

                # 判断库存
                if sku_count > sku.stock:
                    return redirect(reverse('goods:detail', kwargs={'sku_id': sku_id}))

                # 计算商品总金额
                amount = sku.price * sku_count
                # 将商品数量和金额封装到sku对象
                sku.count = sku_count
                sku.amount = amount
                skus.append(sku)

                # 金额和数量求和
                total_count += sku_count
                # 所有商品的总价
                total_sku_amount += amount

        # 实付款，含运费，在ifelse外
        total_amount = total_sku_amount + trans_cost

        # 用户地址信息
        try:
            address = Address.objects.filter(user=request.user).latest('create_time')
        except Address.DoesNotExist:
            address = None  # 模板会做判断，然后跳转到地址编辑页面

        # 构造上下文
        context = {
            'skus': skus,  # 商品sku
            'total_count': total_count,  # 总数量
            'total_sku_amount': total_sku_amount,  # 所有商品的总价
            'trans_cost': trans_cost,  # 运费
            'total_amount': total_amount,  # 实付款（含运费）
            'address': address  # 地址对象
        }

        print(context)
        # redis_conn = get_redis_connection()
        # count = redis_conn.hget(1, 44)
        # print('count=',count)  # 值为None
        # count = redis_conn.hget('cart_%s' % request.user.id, 44)
        # print('count=',count)  # 值为None
        # count = redis_conn.hget('cart_%s' % request.user.id, 1)
        # print('count=',count)
        # count = redis_conn.hget('cart_%s' % request.user.id, '1')
        # print('count=',count)

        # 响应结果:html页面
        return render(request, 'place_order.html', context)


class CommitOrderView(LoginRequiredJSONMinix, View):
    """提交订单"""

    def post(self, request):
        """

        :param request:
        :return: 返回json数据，以便前端根据返回重定向
        """
        # 获取参数：user,address_id,pay_method,sku_id,count
        user = request.user
        address_id = request.POST.get('address_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')  # 好像没传？  '1,2,3,4,5' 字符串
        sku_ids = sku_ids.split(',')

        # count = request.POST.get('count')  # 没传啊？
        print('[address_id, sku_ids, pay_method]=', [address_id, sku_ids, pay_method])
        # 校验参数：all([address_id, sku_ids, pay_method])
        if not all([address_id, sku_ids, pay_method]):
            return JsonResponse({'code': 2, 'msg': '参数不完整'})

        # 判断地址
        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            return JsonResponse({'code': 3, 'msg': '地址错误'})

        # 判断支付方式
        if pay_method not in OrderInfo.PAY_METHODS:
            return JsonResponse({'code': 4, 'msg': '支付方式错误'})

        redis_conn = get_redis_connection('default')
        # 遍历sku_ids，
        for sku_id in sku_ids:
            try:
                # 循环取出sku
                sku = GoodsSKU.objects.get(id=sku_id)
                # 判断商品是否存在
            except GoodsSKU.DoesNotExist:
                # # 这里，为了能让客户先买东西，所以找到无效商品直接跳过，先让他买去吧
                # continue
                return JsonResponse({'code': 5, 'msg': '商品不存在'})
            else:
                # 获取商品数量，判断库存 (redis)
                # 为什么能从redis中获取count？
                    # 分析：在购物车中，你只可以选择某种商品你买不买，但是你不能选择这种商品买了、但是只买购物车数量的一部分
                    # 所以，这里只要sku存在，那sku_id必然同时存在于购物车redis中，且redis中的count，就是要买的sku的count
                # try:
                # except Exception as e:
                # 即使sku_id不存在，也能获取，值为None
                count = redis_conn.hget('cart_%s' % user.id, sku_id)

                if not count:
                    return JsonResponse({'code': 6, 'msg': '商品数量不对'})

                if count > sku.stock:
                    return JsonResponse({'code': 7, 'msg': '商品库存不足'})


                # 保存订单商品数据OrderGoods(能执行到这里说明无异常)
                OrderGoods.objects.create({
                    'order':order,        # 订单 外键
                    'sku':sku,            # 订单商品
                    'count':count,        # 数量
                    'price':price,        # 历史单价
                     'comment':comment    # 评价信息
                })

        # 先创建商品订单信息

        # 减少sku库存

        # 增加sku销量

        # 计算总数和总金额

        # 修改订单信息里面的总数和总金额(OrderInfo)

        # 订单生成后删除购物车(hdel)

        # 响应结果
        return JsonResponse({'code': 0, 'message': '下单成功'})
