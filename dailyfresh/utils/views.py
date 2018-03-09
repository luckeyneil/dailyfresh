from django.contrib.auth.decorators import login_required
from django.utils.decorators import classonlymethod


class LoginRequiredMinix(object):
    """验证已登录状态专用类"""
    # @classmethod
    @classonlymethod   # 只能在此类中调用
    def as_view(self, **initkwargs):
        # 只能由同时继承了此类和View类的子类调用
        view = super().as_view()
        return login_required(view)   # 验证



