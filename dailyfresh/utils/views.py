from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.decorators import classonlymethod
from django.utils.six import wraps


class LoginRequiredMinix(object):
    """验证已登录状态专用类"""

    # @classmethod
    @classonlymethod  # 只能在此类中调用
    def as_view(self, **initkwargs):
        # 只能由同时继承了此类和View类的子类调用
        view = super().as_view()
        return login_required(view)  # 验证


def login_required_json(view_func):
    # 还原原方法的方法名和注释
    @wraps(view_func)
    def login_command(request, *args, **kwargs):
        if request.user.is_authenticated():
            # 如果登录，返回执行视图
            return view_func(request, *args, **kwargs)
        else:
            # 如果未登录，返回json数据
            return JsonResponse({'code': 1, 'msg': '未登录，请登录'})

    return login_command


class LoginRequiredJSONMinix(object):
    """验证JSON已登录状态专用类"""

    # @classmethod
    @classonlymethod  # 只能在此类中调用
    def as_view(self, **initkwargs):
        # 只能由同时继承了此类和View类的子类调用
        view = super().as_view()
        return login_required_json(view)  # 验证
