import json

from django.core.cache import cache
from django.core.paginator import EmptyPage, Paginator
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect
from django.views.generic import View

# Create your views here.
from django_redis import get_redis_connection

from goods.models import *


class BaseCartView(View):
    """提取出的添加购物车的基类"""

    def get_cart_num(self, request):
        """
        专门用来提取返回两种情况下的购物车数量
        :param request:
        :return:
        """
        # 查询购物车信息：不能被缓存，因为会经常变化
        cart_num = 0
        # 如果用户登录，就获取购物车数据
        if request.user.is_authenticated():
            # 创建redis_conn对象
            redis_conn = get_redis_connection('default')
            # 获取用户id
            user_id = request.user.id
            # 从redis中获取购物车数据，返回字典
            cart_dict = redis_conn.hgetall('cart_%s' % user_id)
            # 遍历购物车字典的值，累加购物车的值
            for value in cart_dict.values():
                cart_num += int(value)

        else:
            # 如果用户未登录，就获取cookie中数据
            cart_json = request.COOKIES.get('cart')  # json字符串
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

            # 4.
            # 将(cart_dict)
            # 重新生成json字符串，方便写入到cookie
            cart_json = json.dumps(cart_dict)
            # cart_json = str(cart_dict)

            # 7.
            # 计算购物车数量总和，方便前端展示
            # cart_num = 0
            for val in cart_dict.values():
                cart_num += val

        print(cart_num)
        return cart_num


class IndexView(BaseCartView):
    """
    主页信息展示
    """

    def get(self, request):
        """
        展示主页信息
        :param request:
        :return:
        """
        # 从缓存中获取缓存页面数据
        context = cache.get('index_page_data')
        # print(context)

        if context is None:
            print('生成index缓存')
            # 获取用户个人信息对象
            # request.user

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
                title_goods = IndexCategoryGoodsBanner.objects.filter(category=category, display_type=0).order_by(
                    'index')
                category.title_goods = title_goods
                # 图片类商品
                picture_goods = IndexCategoryGoodsBanner.objects.filter(category=category, display_type=1).order_by(
                    'index')
                category.picture_goods = picture_goods

            context = {
                'categorys': categorys,  # 获取商品分类信息查询集,查询集内元素含有分类详情商品查询集
                'banners': banners,  # 获取轮播图查询集
                'promotion_banners': promotion_banners,  # 获取广告图查询集
            }

            # 设置缓存数据：名字，内容，有效期
            cache.set('index_page_data', context, 3600)

        else:
            print('提取index缓存数据')

        # 调用父类的提取购物车数量的方法
        cart_num = self.get_cart_num(request)

        # 补充购物车数据
        # context.update(cart_num=cart_num)
        context['cart_num'] = cart_num

        return render(request, 'index.html', context)


class DetailView(BaseCartView):
    """商品详细信息页面"""

    def get(self, request, sku_id):
        # 尝试获取缓存数据
        context = cache.get("detail_%s" % sku_id)

        # 如果缓存不存在
        if context is None:
            print('生成detail缓存')
            try:
                # 获取商品信息
                sku = GoodsSKU.objects.get(id=sku_id)
            except GoodsSKU.DoesNotExist:
                # from django.http import Http404
                # raise Http404("商品不存在!")
                return redirect(reverse("goods:index"))

            # 获取类别
            categorys = GoodsCategory.objects.all()

            # 从订单中获取评论信息
            sku_orders = sku.ordergoods_set.all().order_by('-create_time')[:30]
            if sku_orders:
                for sku_order in sku_orders:
                    sku_order.ctime = sku_order.create_time.strftime('%Y-%m-%d %H:%M:%S')
                    sku_order.username = sku_order.order.user.username
            else:
                sku_orders = []

            # 获取最新推荐
            new_skus = GoodsSKU.objects.filter(category=sku.category).order_by("-create_time")[:2]

            # 获取其他规格的商品
            other_skus = sku.goods.goodssku_set.exclude(id=sku_id)

            context = {
                "categorys": categorys,
                "sku": sku,
                "orders": sku_orders,
                "new_skus": new_skus,
                "other_skus": other_skus
            }

            # 设置缓存
            cache.set("detail_%s" % sku_id, context, 3600)

        else:
            print('提取缓存detail数据')

        # 购物车数量
        cart_num = self.get_cart_num(request)

        # 如果是登录的用户
        if request.user.is_authenticated():
            # 获取用户id
            user_id = request.user.id
            # 从redis中获取购物车信息
            redis_conn = get_redis_connection("default")
            # # 如果redis中不存在，会返回None
            # cart_dict = redis_conn.hgetall("cart_%s" % user_id)
            # for val in cart_dict.values():
            #     cart_num += int(val)

            # 浏览记录: lpush history_userid sku_1, sku_2
            # 移除已经存在的本商品浏览记录
            redis_conn.lrem("history_%s" % user_id, 0, sku_id)
            # 添加新的浏览记录
            redis_conn.lpush("history_%s" % user_id, sku_id)
            # 只保存最多5条记录
            redis_conn.ltrim("history_%s" % user_id, 0, 4)

        context.update({"cart_num": cart_num})

        return render(request, 'detail.html', context)


# /list/category_id/page_num/?sort='默认，价格，人气'
class ListView(BaseCartView):
    """商品列表"""

    def get(self, request, category_id, page_num):

        # 获取sort参数:如果用户不传，就是默认的排序规则
        sort = request.GET.get('sort', 'default')

        # 校验参数
        # 判断category_id是否正确，通过异常来判断
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return redirect(reverse('goods:index'))

        # 购物车
        cart_num = self.get_cart_num(request)


        # 查询商品所有类别
        categorys = GoodsCategory.objects.all()

        # 查询该类别商品新品推荐
        new_skus = GoodsSKU.objects.filter(category=category).order_by('-create_time')[:2]

        # 查询该类别所有商品SKU信息：按照排序规则来查询
        if sort == 'price':
            # 按照价格由低到高
            skus = GoodsSKU.objects.filter(category=category).order_by('price')
        elif sort == 'hot':
            # 按照销量由高到低
            skus = GoodsSKU.objects.filter(category=category).order_by('-sales')
        else:
            skus = GoodsSKU.objects.filter(category=category)
            # 无论用户是否传入或者传入其他的排序规则，我在这里都重置成'default'
            sort = 'default'

        # 分页：需要知道从第几页展示
        page_num = int(page_num)

        # 创建分页器：每页两条记录
        paginator = Paginator(skus, 1)
        # print('paginator.num_pages=', paginator.num_pages)

        # 校验page_num：只有知道分页对对象，才能知道page_num是否正确
        try:
            page_skus = paginator.page(page_num)
        except EmptyPage:
            # 如果page_num不正确，默认给用户第一页数据
            page_num = 1
            page_skus = paginator.page(1)

        # print(1)
        page_list = paginator.page_range
        # print(page_list)

        # 获取页数列表
        if paginator.num_pages <= 5:
            page_list = page_list
        elif page_num <= 3:
            page_list = page_list[0:5]
        elif page_num >= paginator.num_pages - 2:
            page_list = page_list[paginator.num_pages - 5:paginator.num_pages]
        else:
            page_list = page_list[page_num - 2:page_num + 3]

        # 构造上下文
        context = {
            'sort': sort,
            'category': category,
            'cart_num': cart_num,
            'categorys': categorys,
            'new_skus': new_skus,
            'page_skus': page_skus,
            'page_list': page_list
        }

        # 渲染模板
        return render(request, 'list.html', context)
