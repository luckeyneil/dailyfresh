import json

from django.core.paginator import EmptyPage
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect

# Create your views here.
from django.utils import timezone
from django.views.generic import View
from django_redis import get_redis_connection

from goods.models import GoodsSKU
from orders.models import OrderInfo, OrderGoods
from users.models import Address
from utils.views import LoginRequiredMinix, LoginRequiredJSONMinix, TransactionAtomicMixin


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
        # 获取参数：sku_ids, getlist()会得到列表
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

        redis_conn = get_redis_connection('default')
        user = request.user
        # 查询商品数据
        if count is None:
            # 如果是从购物车页面过来，商品的数量从redis中获取
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
            print('从商品详情页面过来的商品sku_ids=',sku_ids)
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

                # 这里有一个逻辑，当从购物车过来时，你必须将此种商品的count更新，原先不管此种商品有无count，
                # 都直接覆盖掉，产品需求如此
                try:
                    redis_conn.hset('cart_%s'%user.id, sku_id, count)
                    # redis_conn.save()
                except Exception as e:
                    print(e)

                count = redis_conn.hget('cart_%s'%user.id, sku_id)
                print('从商品详情立即购买过来的count=',count)
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

        sku_ids = ','.join(sku_ids)  # sku_ids原先是一个列表

        # 构造上下文
        context = {
            'skus': skus,  # 商品sku
            'total_count': total_count,  # 总数量
            'total_sku_amount': total_sku_amount,  # 所有商品的总价
            'trans_cost': trans_cost,  # 运费
            'total_amount': total_amount,  # 实付款（含运费）
            'address': address,  # 地址对象
            'sku_ids': sku_ids  # 商品id用‘，’组合成的字符串
        }

        # print(context)
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


class CommitOrderView(LoginRequiredJSONMinix, TransactionAtomicMixin, View):
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
        pay_method = int(pay_method)
        sku_ids = request.POST.get('sku_ids')  # 好像没传？  '1,2,3,4,5' 字符串
        sku_ids = sku_ids.split(',')
        print('sku_ids=',sku_ids)
        # count = request.POST.get('count')  # 没传啊？
        print('[address_id, sku_ids, pay_method]=', [address_id, sku_ids, pay_method])
        # 校验参数：all([address_id, sku_ids, pay_method])
        if not all([address_id, sku_ids, pay_method]):
            return JsonResponse({'code': 2, 'msg': '参数不完整'})

        # 判断地址
        try:
            address = Address.objects.get(id=address_id)
            print('address对象存在，是：', address)
        except Address.DoesNotExist:
            return JsonResponse({'code': 3, 'msg': '地址错误'})

        # 判断支付方式
        if pay_method not in OrderInfo.PAY_METHODS:
            print('pay_method正确，是：', pay_method)
            return JsonResponse({'code': 4, 'msg': '支付方式错误'})

        # 手动生成order_id
        order_id = timezone.now().strftime('%Y%m%d%H%M%S') + str(user.id)
        print('order_id:', order_id)

        # 本次订单的商品总数和商品总金额
        total_count = 0
        total_amount = 0
        trans_cost = 10

        # 在生成订单前创建保存点
        savepoint = transaction.savepoint()

        try:
            order = OrderInfo.objects.create(**{
                'order_id': order_id,
                'user': user,
                'address': address,
                # 'total_count': 0,  # 因为有default，就不写了
                'total_amount': total_amount,
                'trans_cost': trans_cost,
                'pay_method': pay_method,
                # 'status': status,   # 有默认值，不写
                # 'trade_id':   # 可为空，不写
            })

            print('order:', order)
            redis_conn = get_redis_connection('default')
            # try:
            # 遍历sku_ids，
            for sku_id in sku_ids:
                for i in range(3):
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
                        print('cart_%s' % user.id, sku_id)
                        count = redis_conn.hget('cart_%s' % user.id, sku_id)
                        print('提交订单前遍历的count=',count)
                        if not count:
                            return JsonResponse({'code': 6, 'msg': '商品数量不对'})

                        count = int(count)
                        if count > sku.stock:
                            return JsonResponse({'code': 7, 'msg': '商品库存不足'})

                        """------------------------不使用锁---------------------------"""
                        # # 减少sku库存
                        # sku.stock -= count
                        # # 增加sku销量
                        # sku.sales += count
                        # sku.save()

                        """------------------------使用乐观锁---------------------------"""

                        # 减少库存,增加销量
                        origin_stock = sku.stock
                        new_stock = origin_stock - count
                        new_sales = sku.sales + count
                        # 更新库存和销量
                        result = GoodsSKU.objects.filter(id=sku_id, stock=origin_stock).update(stock=new_stock,
                                                                                               sales=new_sales)
                        if 0 == result and i < 2:
                            continue  # 还有机会，继续重新下单
                        elif 0 == result and i == 2:
                            # 回滚
                            transaction.savepoint_rollback(savepoint)
                            return JsonResponse({'code': 9, 'message': '下单失败'})
                        # elif result:
                        #     # 如果更新成功，则打断for循环
                        #     break
                    price = sku.price

                    # 保存订单商品数据OrderGoods(能执行到这里说明无异常)
                    OrderGoods.objects.create(**{
                        'order': order,  # 订单 外键
                        'sku': sku,  # 订单商品
                        'count': count,  # 数量
                        'price': price,  # 历史单价
                        # 'comment':comment    # 评价信息,有default，不写
                    })

                    # 计算总数和总金额
                    total_count += count
                    total_amount += count * price
                    # 运行到这里，说明无问题，打断循环
                    break

            # 修改订单信息里面的总数和总金额(OrderInfo)
            order.total_count = total_count
            order.total_sku_amount = total_amount
            order.total_amount = total_amount + trans_cost
            order.save()

        except Exception as e:
            print(e)
            # 出现任何异常都回滚
            transaction.savepoint_rollback(savepoint)
            return JsonResponse({'code': 8, 'msg': '下单失败'})
        else:
            # 没有异常，就手动提交
            transaction.savepoint_commit(savepoint)

        # 订单生成后删除购物车(hdel), 也可用sku_ids列表进行删除，将列表*号拆包
        redis_conn.hdel('cart_%s' % user.id, *sku_ids)
        # 响应结果
        return JsonResponse({'code': 0, 'msg': '下单成功'})


class UserOrdersView(LoginRequiredMinix, View):
    """用户订单页面"""

    def get(self, request, page):
        user = request.user
        # 查询订单
        orders = user.orderinfo_set.all().order_by("-create_time")

        for order in orders:
            order.status_name = OrderInfo.ORDER_STATUS[order.status]
            order.pay_method_name = OrderInfo.PAY_METHODS[order.pay_method]
            order.skus = []
            order_skus = order.ordergoods_set.all()
            for order_sku in order_skus:
                sku = order_sku.sku
                sku.count = order_sku.count
                sku.price = order_sku.price
                sku.amount = order_sku.price * sku.count
                order.skus.append(sku)

        # 分页
        page = int(page)
        try:
            # 创造分页器，每页2条数据
            paginator = Paginator(orders, 2)
            page_orders = paginator.page(page)
        except EmptyPage:
            # 如果传入的页数不存在，就默认给第1页
            page_orders = paginator.page(1)
            page = 1

        # 页数
        page_list = paginator.page_range

        # 获取页数列表
        if paginator.num_pages <= 5:
            page_list = page_list
        elif page <= 3:
            page_list = page_list[0:5]
        elif page >= paginator.num_pages - 2:
            page_list = page_list[paginator.num_pages - 5:paginator.num_pages]
        else:
            page_list = page_list[page - 2:page + 3]

        context = {
            "orders": page_orders,
            "page": page,
            "page_list": page_list,
        }

        return render(request, "user_center_order.html", context)
