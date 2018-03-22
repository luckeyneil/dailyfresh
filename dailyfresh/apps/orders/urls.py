from django.conf.urls import url

from orders import views

urlpatterns = [
    # url(r'^register/$', views.register)
    url(r'^place/$', views.PlaceOrderView.as_view(), name='place'),  # 订单详情页
    url(r'^commit/$', views.CommitOrderView.as_view(), name='commit'),  # 提交订单
    url(r'^(?P<page>\d+)/$', views.UserOrdersView.as_view(), name='info'),  # 所有订单页
    url(r'^pay/$', views.PayView.as_view(), name='pay'), # 支付请求
    url(r'^checkpay/$', views.CheckPayView.as_view(), name='checkpay'), # 检查支付状态
    url('^comment/(?P<order_id>\d+)$', views.CommentView.as_view(), name="comment") # 评论详情页面
]