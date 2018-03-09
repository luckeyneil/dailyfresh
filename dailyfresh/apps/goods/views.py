from django.shortcuts import render
from django.views.generic import View


# Create your views here.
from goods.models import *


class IndexView(View):
    """
    主页信息展示
    """
    def get(self, request):
        """
        展示主页信息
        :param request:
        :return:
        """
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
            title_goods = IndexCategoryGoodsBanner.objects.filter(category=category, display_type=0).order_by('index')
            category.title_goods = title_goods
            # 图片类商品
            picture_goods = IndexCategoryGoodsBanner.objects.filter(category=category, display_type=1).order_by('index')
            category.picture_goods = picture_goods

        # 获取购物车计数
        cart_num = 0

        context = {
            'categorys': categorys,  # 获取商品分类信息查询集,查询集内元素含有分类详情商品查询集
            'banners': banners,   # 获取轮播图查询集
            'promotion_banners': promotion_banners,   # 获取广告图查询集
            'cart_num': cart_num   # 获取购物车计数
        }

        return render(request, 'index.html', context)
