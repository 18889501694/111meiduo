import json
import re

from django.views import View
from django.http import JsonResponse
from django.contrib.auth import logout, login, authenticate
from django_redis import get_redis_connection

from apps.goods.models import SKU
from apps.users.models import User
from apps.users.utils import generic_email_verify_token, check_verify_token
from apps.users.models import Address
from utils.views import LoginRequiredJSONMixin

from celery_tasks.email.tasks import celery_send_email


class UsernameCountView(View):

    def get(self, request, username):
        """
        1.接收用户名，对这个用户名进行以下判断
        2.根据用户名查询数据库（count为1则存在，为0则不存在）
        3.返回响应
        4.if not re.match('[a-zA-Z0-9 -]{5,20}', username):
            return JsonResponse({'code':400 , 'errmsg': '用户名不符合需求'})
        """
        count = User.objects.filter(username=username).count()
        return JsonResponse({'code': 0, 'count': count, 'errmsg': 'ok'})


class RegisterView(View):

    def post(self, request):
        """
        1.接收请求（POST--------JSON）bytes->str->dict， decode(): bytes→字符串 json.loads(): json字符串→字典
        2.获取数据
        3.验证数据
        3.1用户名，密码，确认密码，手机号，是否同意协议都有；
        3.2用户名满足规则，用户名不能重复
        3.3密码满足规则
        3.4确认密码和密码要一致
        3.5手机号码满足规则。手机号码也不能重复
        3.6需要同意协议
        4.数据入库两者方式，但是都没有加密
        5.返回响应
        """
        body_dict = json.loads(request.body.decode())
        username = body_dict.get('username')
        password = body_dict.get('password')
        password2 = body_dict.get('password2')
        mobile = body_dict.get('mobile')
        allow = body_dict.get('allow')

        if not all([username, password, password2, mobile, allow]):
            return JsonResponse({'code': 400, 'errmsg': '参数不全'})
        if not re.match('[a-zA-Z_-]{5,20}', username):
            return JsonResponse({'code': 400, 'errmsg': '用户名不满足规则'})

        # user = User(username=username, password=password, mobile=mobile)
        # user.save()
        # User.objects.create(username=username, password=password, mobile=mobile)

        user = User.objects.create_user(username=username, password=password, mobile=mobile)
        request.session["user_id"] = user.id
        login(request, user)

        return JsonResponse({'code': 0, 'errmsg': 'ok'})


class LoginView(View):

    def post(self, request):
        """
        1.接收数据
        2.验证数据
        2.1确定我们是根据手机号查询还是根据用户名查询,USERNAME_FIELD我们可以根据修改User,USERNAME_FILD字段来影响authenticate的查询
        3.验证用户名和密码是否正确，可以通过用户模型的用户名来查询 User.objects.get(username=username)
        4.authenticate传递用户名和密码
        4.1如果用户名和密码正确，则返回User信息
        4.2如果用户名和密码不正确，则返回None
        5.判断是否记住登录,None默认值2周,0则为不记住
        6.返回响应
        """
        data = json.loads(request.body.decode())
        username = data.get('username')
        password = data.get('password')
        remembered = data.get('remembered')

        if not all([username, password]):
            return JsonResponse({'code': 400, 'errmsg': '参数不全'})
        if re.match('1[3-9]\d{9}', username):
            User.USERNAME_FIELD = 'mobile'
        else:
            User.USERNAME_FIELD = 'username'
        user = authenticate(username=username, password=password)

        if user is None:
            return JsonResponse({'code': 400, 'errmsg': '账号或密码错误'})
        login(request, user)
        if remembered:
            request.session.set_expiry(None)
        else:
            request.session.set_expiry(0)
        response = JsonResponse({'code': 0, 'errmsg': 'ok'})
        response.set_cookie('username', username)  # 为了首页显示用户信息

        return response


class LogoutView(View):

    def delete(self, request):
        # 删除session信息，前端根据cookie信息来判断用户是否登录
        logout(request)
        response = JsonResponse({'code': 0, 'errmsg': 'ok'})
        response.delete_cookie('username')

        return response


class CenterView(LoginRequiredJSONMixin, View):

    def get(self, request):
        """
        1.request.user就是已经登录的用户信息
        2.request.user是来源于中间件
        3.系统会进行判断，如果我们确实是登录用户，就可以取到登录用户相对应的模型实例数据
        4.如果我们不是登录用户，则request.user=AnonymousUser()匿名用户
        """
        info_data = {
            'username': request.user.username,
            'email': request.user.email,
            'mobile': request.user.mobile,
            'email_active': request.user.email_active,
        }

        return JsonResponse({'code': 0, 'errmsg': 'ok', 'info_data': info_data})


class EmailsView(View):

    def put(self, request):
        """
        1.接收请求（post put------body）
        2.获取数据（正则验证）
        3.保存邮箱地址（request.user就是登录用户的实例对象  user-->User）
        4.发送一封激活邮件（subject是主题,html_message/message是邮件内容， from_email是发件人 ，recipient_list是收件人列表）
        4.1对a标签的连接数据进行加密处理
        4.2组织我们的激活邮件
        5.返回响应
        """
        data = json.loads(request.body.decode())
        email = data.get('email')
        user = request.user
        user.save()
        subject = '美多商城激活邮件'
        message = ''
        from_email = '美多商城<qi_rui_hua@163.com>'
        recipient_list = ['qi_rui_hua@163.com']

        token = generic_email_verify_token(request.user.id)
        verify_url = 'http://www.meiduo.site:8080/success_verify_email.html?token=%s' % token

        html_message = '<p>尊敬的用户你好！</p>' \
                       '<p>感谢你使用美多商城。</p>' \
                       '<p>你的邮箱为：{} 请你点击此链接激活你的邮箱：</p>' \
                       '<p>a href="{}">{}<a></p>'.format(email, verify_url, verify_url)

        # html_message = "点击按钮进行激活<a href='http://www.itcast.cn/？token={}'>激活</a>".format(token)
        # send_mail(subject=subject,
        #           message=message,
        #           from_email=from_email,
        #           recipient_list=recipient_list,
        #           html_message=html_message)

        celery_send_email.delay(subject=subject,
                                message=message,
                                from_email=from_email,
                                recipient_list=recipient_list,
                                html_message=html_message
                                )

        return JsonResponse({'code': 0, 'errmsg': 'ok'})


class EmailVerifyView(View):

    def put(self, request):
        """
        1.接收请求 2.获取参数 3.验证参数 4.获取user_id 5.根据用户id查询数据 7.返回响应json
        """
        params = request.GET
        token = params.get('token')
        if token is None:
            return JsonResponse({'code': 400, 'errmsg': '参数缺失'})

        user_id = check_verify_token(token)
        if user_id is None:
            return JsonResponse({'code': 400, 'errmsg': '参数错误'})

        user = User.objects.get(id=user_id)
        user.email_active = True
        user.save()

        return JsonResponse({'code': 0, 'errmsg': 'ok'})


class AddressCreateView(LoginRequiredJSONMixin, View):
    """新增地址"""

    def post(self, request):
        """
        1.接收请求 2.获取参数，验证参数 2.1验证必传参数 2.2有市区的id是否正确 2.3详细地址的长度
        2.4手机号 2.5固定电话 2.6邮箱
        3.数据入库
        4.返回响应
        """
        data = json.loads(request.body.decode())
        receiver = data.get('receiver')
        province_id = data.get('province_id')
        city_id = data.get('city_id')
        district_id = data.get('district_id')
        place = data.get('place')
        mobile = data.get('mobile')
        tel = data.get('tel')
        email = data.get('email')

        user = request.user

        address = Address.objects.create(
            user=user,
            title=receiver,
            receiver=receiver,
            province_id=province_id,
            city_id=city_id,
            district_id=district_id,
            place=place,
            mobile=mobile,
            tel=tel,
            email=email,
        )
        address_dict = {
            'id': address.id,
            'title': address.title,
            'receiver': address.receiver,
            'province': address.province.name,
            'city': address.city.name,
            'district': address.district.name,
            'place': address.place,
            'mobile': address.mobile,
            'tel': address.tel,
            'email': address.email,
        }

        return JsonResponse({'code': 0, 'errmsg': 'ok', 'address': address_dict})


class AddressView(LoginRequiredJSONMixin, View):
    """地址的查询"""

    def get(self, request):
        """
        1.查询指定数据
        2.将对象数据转成字典数据
        3.
        """
        user = request.user
        addresses = Address.objects.filter(user=user, is_deleted=False)
        address_list = []
        for address in addresses:
            address_list.append({
                'id': address.id,
                'title': address.title,
                'receiver': address.receiver,
                'province': address.province.name,
                'city': address.city.name,
                'district': address.district.name,
                'place': address.place,
                'mobile': address.mobile,
                'tel': address.tel,
                'email': address.email,
            })
            return JsonResponse({'code': 0, 'errmsg': 'ok', 'address': address_list})


class UserHistoryView(LoginRequiredJSONMixin, View):
    """
    1、用户浏览记录添加实现
    2、展示用户浏览记录
    """

    def post(self, request):
        """
        1、接收请求 2、获取请求参数 3、验证参数 4、连接redis
        5、去重（先删除这个商品id 数据 再添加就可以了）
        6、保存到redis中  7、只保存5条记录
        8、返回json
        """
        user = request.user
        data = json.loads(request.body.decode())
        sku_id = data.get('sku_id')
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return JsonResponse({'code': 400, 'errmsg': '没有此商品'})

        redis_cli = get_redis_connection('history')
        redis_cli.lrem('history_%s' % user.id, sku_id)
        redis_cli.lpush('history_%s' % user.id, sku_id)
        redis_cli.ltrim('history_%s' % user.id, 0, 4)

        return JsonResponse({'code': 0, 'errmsg': 'ok'})

    def get(self, request):
        """
        1、连接redis
        2、获取redis数据
        3、根据商品id进行数据查询
        4、将对象转换为字典
        5、返回json
        """
        redis_cli = get_redis_connection('history')
        ids = redis_cli.lrange('history_%s' % request.user.id, 0, 4)
        history_list = []
        for sku_id in ids:
            sku = SKU.objects.get(id=sku_id)
            history_list.append({
                'id': sku.id,
                'name': sku.name,
                'default_image_url': sku.default_image.url,
                'price': sku.price
            })

        return JsonResponse({'code': 0, 'errmsg': 'ok', 'skus': history_list})
