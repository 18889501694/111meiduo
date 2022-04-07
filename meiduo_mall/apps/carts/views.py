import json
import pickle
import base64

from django.http import JsonResponse
from django.views import View
from django_redis import get_redis_connection

from apps.goods.models import SKU


class CartsView(View):
    """
    1、添加购物车
    2、购物车的展示
    """

    def post(self, request):
        """
        1、接收数据  2、验证数据
        3、判断用户的登录状态（request.user关联User的模型数据 用is_authenticated=True来验证用户 False是匿名用户）

        4、登录用户购物车保存redis：1、连接redis 2、操作hash 3、操作set 4、返回响应
                                redis中hash用法 :redis_cli.hset(key,field,value)  set的用法:redis_cli.sadd(key,field)

        5、未登录用户保存cookie：1、先读取cookie数据进行判断   2、先有cookie字典    3、字典转换为bytes
                    4、bytes类型数据base64编码(base64encode.decode()的作用是将bytes类型转换为str) 5、设置cookie  6、返回响应
        """
        data = json.loads(request.body.decode())
        sku_id = data.get('sku_id')
        count = data.get('count')

        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return JsonResponse({'code': 400, 'errmsg': '查无此商品'})

        # 类型强制转换
        try:
            count = int(count)
        except Exception:
            count = 1

        user = request.user
        if user.is_authenticated:
            redis_cli = get_redis_connection('carts')
            redis_cli.hset('carts_%s' % user.id, sku_id, count)
            redis_cli.add('selected_%s' % user.id, sku_id)
            return JsonResponse({'code': 0, 'errmsg': 'ok'})
        else:
            cookie_carts = request.COOKIES.get('carts')
            if cookie_carts:
                carts = pickle.loads(base64.b64decode(cookie_carts))
            else:
                carts = {}

            if sku_id in carts:
                # 购物车中已经有商品id 数量累加
                origin_count = carts[sku_id]['count']
                count += origin_count

            carts[sku_id] = {'count': count, 'selected': True}
            carts_bytes = pickle.dumps(carts)
            base64encode = base64.b64encode(carts_bytes)
            response = JsonResponse({'code': 0, 'errmsg': 'ok'})
            response.set_cookie('carts', base64encode.decode(), max_age=3600 * 24 * 12)
            return response

    def get(self, request):
        """
        1、判断用户是否登录
        2、登录用户查询redis（1、连接redis 2、hash  3、set  4、将redis数据转换为和cookie一样可以方便后续操作）
        3、未登录用户查询cookie（1、读取cookie数据 2、判断是否存在购物车数据 3、如果存在则解码，不存在就空字典）
        4、根据商品id查询商品信息（可以直接遍历carts也可以获取字典的最外层的key，最外层的所有key就是商品id）
        5、将对象数据转换为字典数据
        """
        user = request.user
        if user.is_authenticated:
            redis_cli = get_redis_connection('carts')
            sku_id_counts = redis_cli.hgethall('carts_%s' % user.id)
            selected_ids = redis_cli.smembers('selected_%s' % user.id)
            carts = {}

            for sku_id, count in sku_id_counts.items():
                carts[sku_id] = {'count': count, 'selected': sku_id in selected_ids}  # 结果是True或是FALSE
            else:
                cookie_carts = request.COOKIES.get('carts')
                if cookie_carts:
                    carts = pickle.loads(base64.b64decode(cookie_carts))
                else:
                    carts = {}

        sku_ids = carts.keys()
        # 可以遍历查询 也可以使用in查询
        skus = SKU.objects.filter(id__in=sku_ids)

        sku_list = []
        for sku in skus:
            sku_list.append({
                'id': sku.id,
                'price': sku.price,
                'name': sku.name,
                'default_image_url': sku.default_image.url,
                'selected': carts[sku.id]['selected'],
                'count': carts[sku.id]['count'],
                'amount': sku.price * carts[sku.id]['count'],
            })
        return JsonResponse({'code': 0, 'errmsg': 'ok', 'cart_skus': sku_list})
