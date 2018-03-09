from django.contrib import admin

from goods.models import *
# Register your models here.

admin.site.register(GoodsCategory)              # 商品类别表
admin.site.register(Goods)                      # 商品SPU表
admin.site.register(GoodsSKU)                   # 商品SKU表
admin.site.register(GoodsImage)                 # 商品图片
admin.site.register(IndexGoodsBanner)           # 主页轮播商品展示
admin.site.register(IndexCategoryGoodsBanner)   # 主页分类商品展示
admin.site.register(IndexPromotionBanner)       # 主页促销活动展示
