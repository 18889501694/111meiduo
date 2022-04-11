from django.views import View
from django.http import HttpResponse, JsonResponse
from django_redis import get_redis_connection

from libs.captcha.captcha import ImageCaptcha
from celery_tasks.sms.tasks import celery_send_sms_code

from random import randint


class ImageCodeView(View):
    """图片验证码"""

    def get(self, request, uuid):
        """
        1.接收路由中的uuid
        2.生成图片验证码和图片二进制
        3.通过redis把图片验证码保存起来
        3.1进行redis的连接
        3.2指令操作  name,time，value
        4.返回图片二进制
        4.1因为图片是二进制，不能返回JSON数据
        """
        text, image = ImageCaptcha.generate_captcha()
        redis_cli = get_redis_connection('code')
        redis_cli.setex(uuid, 100, text)

        return HttpResponse(image, content_type='image/png')


class SmsCodeView(View):
    """短信验证码"""

    def get(self, request, mobile):
        """
        1.获取请求参数
        2.验证参数
        3.验证图片验证码 3.1连接redis 3.2获取redis数据 3.3对比验证码 3.4提取发送短信的标记，看看有没有
        4生成短信验证 4.1增加服务器与redis之间管道 4.2将redis请求添加到队列 4.3执行请求
        5.保存短信验证码 5.1添加一个发送标记，有效期为60秒，内容是什么都可以
        6.发送短信验证码
        6.1开启celery任务，delay的参数等同于任务（函数）的参数
        7.返回响应
        """
        image_code = request.GET.get('image_code')
        uuid = request.GET.get('image_code_id')

        if not all([image_code, uuid]):
            return JsonResponse({'code': 400, 'errmsg': '参数不全！'})

        redis_cli = get_redis_connection('code')
        redis_image_code = redis_cli.get(uuid)
        if redis_image_code is None:
            return JsonResponse({'code': 400, 'errmsg': '图片验证码已经过期！'})
        if redis_image_code.decode().lower() != image_code.lower():
            return JsonResponse({'code': 400, 'errmsg': '图片验证错误！'})

        send_flag = redis_cli.get('send_flag_{}'.format(mobile))
        if send_flag is not None:
            return JsonResponse({'code': 400, 'errmsg': '请不要重复发送短信验证'})
        sms_code = '%06d' % randint(0, 9999999)

        pipeline = redis_cli.pipeline()
        pipeline.setex('sms_{}'.format(mobile), 300, sms_code)
        pipeline.setex('sms_flag_{}'.format(mobile), 60, 1)
        pipeline.execute()

        redis_cli.setex(mobile, 300, sms_code)
        redis_cli.setex('send_flag_{}'.format(mobile), 60, 1)

        #  6.发送短信验证码
        # from libs.yuntongxun.sms import CCP
        # CCP().send_template_sms(mobile, [sms_code, 5], 1)

        celery_send_sms_code.delay(mobile, sms_code)
        return JsonResponse({'code': 0, 'errmsg': 'ok'})
