from django.conf.urls import url

from goods import views

urlpatterns = [
    # url(r'^register/$', views.register)
    url(r'^$', views.index, name='index'),
]