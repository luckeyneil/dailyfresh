from django.contrib import admin
# from celerytasks.tasks import generate_static_index_html
from celerytasks import tasks
from goods.models import *


# Register your models here.


class BaseAdmin(admin.ModelAdmin):
    """商品活动信息的管理类,运营人员在后台发布内容时，异步生成静态页面"""

    def save_model(self, request, obj, form, change):
        """后台保存对象数据时使用"""

        # obj表示要保存的对象，调用save(),将对象保存到数据库中
        obj.save()
        # 调用celery异步生成静态文件方法
        tasks.generate_static_index_html.delay()

    def delete_model(self, request, obj):
        """后台保存对象数据时使用"""
        obj.delete()
        tasks.generate_static_index_html.delay()


# @admin.register(IndexPromotionBanner)
class IndexPromotionBannerAdmin(BaseAdmin):
    """商品活动站点管理，如果有自己的新的逻辑也是写在这里"""
    # list_display = []
    pass


# @admin.register(GoodsCategory)
class GoodsCategoryAdmin(BaseAdmin):
    pass


# @admin.register(Goods)
class GoodsAdmin(BaseAdmin):
    pass


# @admin.register(GoodsSKU)
class GoodsSKUAdmin(BaseAdmin):
    pass


class IndexGoodsBannerAdmin(BaseAdmin):
    pass


# @admin.register(IndexCategoryGoodsBanner)
class IndexCategoryGoodsBannerAdmin(BaseAdmin):
    pass


admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)  # 主页促销活动展示
admin.site.register(GoodsCategory, GoodsCategoryAdmin)  # 商品类别表
admin.site.register(Goods, GoodsAdmin)  # 商品SPU表
admin.site.register(GoodsSKU, GoodsSKUAdmin)  # 商品SKU表
# admin.site.register(GoodsImage,)  # 商品图片
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin)  # 主页轮播商品展示
admin.site.register(IndexCategoryGoodsBanner, IndexCategoryGoodsBannerAdmin)  # 主页分类商品展示
