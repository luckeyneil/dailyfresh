from django.conf.urls import url

from cart import views

urlpatterns = [
    # url(r'^register/$', views.register)
    url(r'^add/$', views.AddCartView.as_view(), name='add'),
]