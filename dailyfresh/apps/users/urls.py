from django.conf.urls import url

from users import views

urlpatterns = [
    url(r'^register/$', views.RegisterView.as_view(), name='register'),
    url(r'^active/(?P<token>.+)$', views.ActiveView.as_view(), name='active'),
    url(r'^login/$', views.LoginView.as_view(), name='login'),
    # url(r'^$', views.index, name='index'),
    url(r'^logout/$', views.LogoutView.as_view(), name='logout'),
    url(r'^address/$', views.AddressView.as_view(), name='address'),
    url(r'^info/$', views.InfoView.as_view(), name='info'),
    url(r'^order/$', views.OrderView.as_view(), name='order'),
]