import json

from django.contrib.auth import login
from django.views import View
from django.http import JsonResponse

from meiduo_mall import settings
from apps.users.models import User
from apps.oauth.models import OAuthQQUser
from apps.oauth.utils import generic_openid, check_access_token

from QQLoginTool.QQtool import OAuthQQ


class QQLoginURLView(View):

    def get(self, request):
        """
        1.生成QQLoginTool实例对象
        2.调用对象的方法生成跳转链接
        3.返回响应,常见404路由不匹配 405请求不被允许(没有实现请求对应的方法)
        """
        qq = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                     client_secret=settings.QQ_CLIENT_SECRET,
                     redirect_uri=settings.QQ_REDIRECT_URL,
                     state='xxxx')
        qq_login_url = qq.get_qq_url()

        return JsonResponse({'code': 0, 'errmsg': 'ok', 'login_url': qq_login_url})


class OauthQQView(View):

    def get(self, request):
        """
        1.获取code
        2.通过code换取token
        3.再通过token换取openid
        4.根据openid进行判断
        5.如果没有绑定过，则需要绑定
        6.如果绑定过，则直接登录 6.1设置session 6.2设置cookie
        """
        code = request.GET.get('code')
        if code is None:
            return JsonResponse({'code': 400, 'errmsg': '参数不全'})
        qq = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                     client_secret=settings.QQ_CLIENT_SECRET,
                     redirect_uri=settings.QQ_REDIRECT_URL,
                     state='xxxx')
        token = qq.get_access_token(code)
        openid = qq.get_open_id(token)
        try:
            qquser = OAuthQQUser.objects.get('openid=openid')
        except OAuthQQUser.DoesNotExist:
            access_token = generic_openid(openid)  # 加密
            response = JsonResponse({'code': 400, 'access_token': access_token})
            return response
        else:
            login(request, qquser.user)
            response = JsonResponse({'code': 0, 'errmsg': 'ok'})
            response.set_cookie('username', qquser.user.username)

            return response

    def post(self, request):
        """
        1.接收请求
        2.获取请求参数 openid
        3.根据手机号进行用户信息的查询
        # 4.手机号不存在，创建一个user信息，然后再绑定
        # 5.手机号存在，已经注册，验证密码是否正确，正确就直接绑定保存，用户和openid信息
        # 6.完成状态保持
        # 7.返回响应
        """
        data = json.loads(request.body.decode())
        mobile = data.get('mobile')
        password = data.get('password')
        sms_code = data.get('sms_code')
        access_token = data.get('access_token')

        openid = check_access_token(access_token)  # 解密
        if openid is None:
            return JsonResponse({'code': 400, 'errmsg': '参数缺失'})
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            user = User.objects.create_user(username=mobile, mobile=mobile, password=password)
        else:
            if not user.check_passwprd(password):
                return JsonResponse({'code': 400, 'errmsg': '账号或密码错误'})

        OAuthQQUser.objects.create(user=user, openid=openid)
        login(request, user)
        response = JsonResponse({'code': 0, 'errmsg': 'ok'})
