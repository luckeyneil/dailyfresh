from django.conf.urls import url, include

from goods import views

urlpatterns = [
    # url(r'^register/$', views.register)
    url(r'^tinymce/', include('tinymce.urls')),
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^index/$', views.IndexView.as_view(), name='index'),
]