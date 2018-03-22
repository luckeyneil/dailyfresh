import json
import os

import time
from alipay import AliPay
from django.conf import settings
from django.core.cache import cache
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


class PlaceOrderView(View):
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

        if not request.user.is_authenticated():
            # 因为如果用继承父类的方法去验证登录的话，若未登录，则直接调整钻到登录页面，
            # 没办法在跳转前把数据存放起来，故故只能自己在订单页里判断登录与否，
            # 若未登录，在保存数据到cookie中之后，将页面跳转到登录页面去
            try:
                count = int(count)
            except:
                return redirect(reverse('goods:index'))

            cart_dict = {}
            for sku_id in sku_ids:
                cart_dict[sku_id] = count
            cart_json = json.dumps(cart_dict)
            response = redirect('/users/login/?next=/cart/')
            response.set_cookie('cart', cart_json)
            return response

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
            print('从商品详情页面过来的商品sku_ids=', sku_ids)
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
                    redis_conn.hset('cart_%s' % user.id, sku_id, count)
                    # redis_conn.save()
                except Exception as e:
                    print(e)

                count = redis_conn.hget('cart_%s' % user.id, sku_id)
                print('从商品详情立即购买过来的count=', count)
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
        print('sku_ids=', sku_ids)
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

        """-------------------------在生成订单前创建保存点--------------------------"""
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
                        # 注意，里面的每个异常都需要执行回滚操作
                        transaction.savepoint_rollback(savepoint)
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
                        print('提交订单前遍历的count=', count)
                        if not count:
                            # 注意，里面的每个异常都需要执行回滚操作
                            transaction.savepoint_rollback(savepoint)
                            return JsonResponse({'code': 6, 'msg': '商品数量不对'})

                        count = int(count)
                        if count > sku.stock:
                            # 注意，里面的每个异常都需要执行回滚操作
                            transaction.savepoint_rollback(savepoint)
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
            """------------------------出现任何异常都回滚------------------------------"""
            transaction.savepoint_rollback(savepoint)
            return JsonResponse({'code': 8, 'msg': '下单失败'})
        else:
            """-------------------------没有异常，就手动提交----------------------------"""
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
                """
                --------------------------------------------------------------------
                这里的唯一目的，是要保存一个固定的历史单价，历史数量，所以，才会把订单商品的
                单价和数量赋值给sku对象。
                想一想，这次修改了sku对象之后，下次再提取出sku对象，sku对象里面的单价和数量是
                我下面赋值给他的？还是数据库里面的？答案当然是数据库里面的，这里只是临时赋值，
                并没有保存到数据库中，只是为了在html页面中方便调用而已。
                那不赋值行不行？
                当然行，因为历史单价和数量早已经保存在订单商品表中了。
                --------------------------------------------------------------------
                """
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


class PayView(LoginRequiredJSONMinix, View):
    """点击支付的请求，json，post"""

    def post(self, request):
        """

        :param request:
        :return:
        """
        order_id = request.POST.get('order_id')  # 获取订单的订单的id

        if not order_id:
            return JsonResponse({'code':2, 'msg':'订单号为空'})

        """----------根据商品订单号 查询当前订单里的所有的商品----------"""

        # 条件1 订单号存在
        # 条件2 订单属于当前的用户
        # 条件3 只有状态是待支付1 的时候 才能支付
        # 条件4  只有支付方式是支付宝
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=request.user,
                                          status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'],
                                          pay_method=OrderInfo.PAY_METHODS_ENUM['ALIPAY'])
        except OrderInfo.DoesNotExist:
            return JsonResponse({'code': 3, 'msg': '订单错误'})


        # 读取公钥私钥的信息
        private_path = os.path.join(settings.BASE_DIR, 'apps/orders/app_private_key.pem')
        public_path = os.path.join(settings.BASE_DIR, 'apps/orders/alipay_public_pay.pem')
        app_private_key_string = open(private_path).read()
        alipay_public_key_string = open(public_path).read()

        # 创建alipay对象,进行各种有关alipay的操作
        alipay = AliPay(
            appid="2016091100483591",  # 注册的应用的id
            app_notify_url=None,  # 默认回调url，公网才能用
            app_private_key_string=app_private_key_string,
            alipay_public_key_string=alipay_public_key_string,  # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # 只能 RSA2
            debug=True  # 默认False,用沙箱模式，改为True
        )

        # 发送支付请求， 返回url后拼接的字符串
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(order.total_amount),  # 这里，部支持decimal，转码为字符串
            subject='天天生鲜订单',
            return_url=None,
            notify_url=None # 可选, 不填则使用默认notify url
        )

        url = settings.ALIPAY_URL + "?" + order_string

        # print('url=',url)

        return JsonResponse({'code':0, 'msg':'发送支付请求成功', 'url': url})


class CheckPayView(LoginRequiredJSONMinix,View):
    """检查支付状态的视图，返回json"""

    def get(self, request):
        """

        :param request:
        :return:
        """
        order_id = request.GET.get('order_id')  # 商品订单号
        print('获取到的order_id=',order_id)

        if not order_id:
            return JsonResponse({'code': 2, 'msg': '订单号错误'})

            # 根据商品订单号 查询当前订单里的所有的商品

        # 条件1 订单号存在
        # 条件2 订单属于当前的用户
        # 条件3 只有状态是待支付1 的时候 才能支付
        # 条件4  只有支付方式是支付宝
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=request.user,
                                          status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'],
                                          pay_method=OrderInfo.PAY_METHODS_ENUM['ALIPAY'])
        except OrderInfo.DoesNotExist:
            return JsonResponse({'code': 3, 'msg': '订单错误'})

        # 读取公钥私钥的信息
        private_path = os.path.join(settings.BASE_DIR, 'apps/orders/app_private_key.pem')
        public_path = os.path.join(settings.BASE_DIR, 'apps/orders/alipay_public_pay.pem')
        app_private_key_string = open(private_path).read()
        alipay_public_key_string = open(public_path).read()

        # 创建alipay对象,进行各种有关alipay的操作
        alipay = AliPay(
            appid="2016091100483591",  # 注册的应用的id
            app_notify_url=None,  # 默认回调url，公网才能用
            app_private_key_string=app_private_key_string,
            alipay_public_key_string=alipay_public_key_string,  # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # 只能 RSA2
            debug=True  # 默认False,用沙箱模式，改为True
        )


        while True:
            # 去支付宝查询当前订单的支付状态
            print('开始查询支付状态')
            try:
                alipay_response = alipay.api_alipay_trade_query(order_id)
            except Exception as e:
                print('e:',e)
                # 为了防止受网络影响导致的查询链接失败报错，所以在查询链接失败时，返回循环再次查询
                continue

            print('已查询到支付状态')

            # 获取响应码和响应信息
            code = alipay_response.get('code')
            trade_status = alipay_response.get('trade_status')

            if code == '10000' and trade_status == 'TRADE_SUCCESS':
                # 支付成功
                # 状态改为未发货
                print('支付成功')
                order.status = OrderInfo.ORDER_STATUS_ENUM['UNSEND']
                # 保存支付宝的交易号
                order.trade_id = alipay_response.get('trade_no')
                # 保存到数据库
                order.save()
                return JsonResponse({'code': 0, 'msg': '支付成功'})
            elif code == '40004' or (code == '10000' and trade_status == 'WAIT_BUYER_PAY'):
                # 再次查询
                print('还在查询中')
                time.sleep(1)
                continue
            else:
                return JsonResponse({'code': 4, 'msg': '支付失败'})


class CommentView(LoginRequiredMinix, View):
    """评论页面"""

    def get(self, request, order_id):
        """提供评论页面"""
        user = request.user
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("orders:info"))

        order.status_name = OrderInfo.ORDER_STATUS[order.status]
        order.skus = []
        order_skus = order.ordergoods_set.all()
        for order_sku in order_skus:
            sku = order_sku.sku
            sku.count = order_sku.count
            sku.amount = sku.price * sku.count
            order.skus.append(sku)

        return render(request, "order_comment.html", {"order": order})

    def post(self, request, order_id):
        """处理评论内容"""
        user = request.user
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("orders:info"))

        # 获取评论条数
        total_count = request.POST.get("total_count")
        total_count = int(total_count)

        for i in range(1, total_count + 1):
            # 要评论的商品
            sku_id = request.POST.get("sku_%d" % i)
            # 获取评论内容
            content = request.POST.get('content_%d' % i, '')
            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue
            # 保存评论到数据库
            order_goods.comment = content
            order_goods.save()

            # 清除商品详情缓存
            cache.delete("detail_%s" % sku_id)

        # 状态变成已完成
        order.status = OrderInfo.ORDER_STATUS_ENUM["FINISHED"]
        order.save()

        return redirect(reverse("orders:info", kwargs={"page": 1}))