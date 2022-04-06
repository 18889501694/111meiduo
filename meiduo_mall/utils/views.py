from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin, AccessMixin


# 第一种方法,继承重写
# class LoginRequiredJSONMixin(AccessMixin):
#     def dispatch(self, request, *args, **kwargs):
#         if not request.user.is_authenticated:
#             return JsonResponse({'code': 400, 'errmsg': '没有登录'})
#         return super().dispatch(request, *args, **kwargs)


# 第二种方法，继承重写
class LoginRequiredJSONMixin(LoginRequiredMixin):
    def handle_no_permission(self):
        return JsonResponse({'code': 400, 'errmsg': '没有登录'})
