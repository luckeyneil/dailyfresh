from django.conf.urls import url

from cart import views

urlpatterns = [
    # url(r'^register/$', views.register)
    url(r'^add/$', views.AddCartView.as_view(), name='add'),
    url(r'^$', views.CartInfoView.as_view(), name='info'),
    url(r'^update/$', views.CartUpdateView.as_view(), name='update'),
    url(r'^delete/$', views.CartDeleteView.as_view(), name='delete'),
]

