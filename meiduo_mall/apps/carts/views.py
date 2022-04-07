import json
import pickle
import base64

from django.http import JsonResponse
from django.views import View
from django_redis import get_redis_connection

from apps.goods.models import SKU


class CartsView(View):
    """
    1、购物车添加（增）
    2、购物车的展示（查）
    3、购物车的修改（改）
    4、购物车的删除（删）
    """

    def post(self, request):
        """
        1、接收数据  2、验证数据
        3、判断用户的登录状态（request.user关联User的模型数据 用is_authenticated=True来验证用户 False是匿名用户）
        4、登录用户购物车保存redis：
            ①、连接redis
            ②、操作hash:redis_cli.hset(key,field,value)
            ③、操作set :redis_cli.sadd(key,field)
            ④、返回响应
        5、未登录用户保存cookie：
            ①、先读取cookie数据进行判断
            ②、先有cookie字典
            ③、字典转换为bytes
            ④、bytes类型数据base64编码(base64encode.decode()的作用是将bytes类型转换为str)
            ⑤、设置cookie
            ⑥、返回响应
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
                'selected': carts[sku.id]['selected'],  # 选中状态
                'count': int(carts[sku.id]['count']),  # 数量强制转换int
                'amount': sku.price * carts[sku.id]['count'],  # 总价格
            })
        return JsonResponse({'code': 0, 'errmsg': 'ok', 'cart_skus': sku_list})

    def put(self, request):
        """
        1、获取用户信息    2、接收数据      3、验证数据
        4、登录用户更新redis（1、连接redis 2、hash  3、set  4、返回响应）
        5、未登录用户更新cookie
        """
        user = request.user
        data = json.loads(request.body.decode())
        sku_id = data.get('sku_id')
        count = data.get('count')
        selected = data.get('selected')

        if not all([sku_id, count]):
            return JsonResponse({'code': 400, 'errmsg': '参数不全'})
        try:
            SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return JsonResponse({'code': 400, 'errmsg': '没有响应'})

        try:
            count = int(count)
        except Exception:
            count = 1

        if user.is_authenticated:
            redis_cli = get_redis_connection('carts')
            redis_cli.hset('carts_%s' % user.id, sku_id, count)
            if selected:
                redis_cli.sadd('selected_%s' % user.id, sku_id)
            else:
                redis_cli.srem('selected_%s' % user.id, sku_id)
            return JsonResponse({'code': 0, 'errmsg': 'ok', 'cart_sku': {'count': count, 'selected': selected}})
        else:
            cookie_carts = request.COOKIES.get('carts')
            if cookie_carts:
                carts = pickle.loads(base64.b64decode(cookie_carts))
            else:
                carts = {}

        if sku_id in carts:
            carts[sku_id] = {'count': count, 'selected': selected}
        new_carts = base64.b64encode(pickle.dumps(carts))
        response = JsonResponse({'code': 0, 'errmsg': 'ok', 'cart_sku': {'count': count, 'selected': selected}})
        response.set_cookie('carts', new_carts.decode(), max_age=14 * 24 * 3600)
        return response

    def delete(self, request):
        """
        1、接收请求  2、验证参数  3、提供用户状态
        4、登录用户操作redis（1、连接redis  2、hash  3、set  4、返回响应）
        5、未登录用户操作cookie（1、判断数据是否存在，存在则解码不存在则空 2、删除数据 3、对字典数据编码和base64 4、设置cookie）
        """
        data = json.loads(request.body.decode())
        sku_id = data.get('sku_id')
        try:
            SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return JsonResponse({'code': 400, 'errmsg': '没有此商品'})

        user = request.user
        if user.is_authenticated:
            redis_cli = get_redis_connection('carts')
            redis_cli.hdel('carts_%s' % user.id, sku_id)
            redis_cli.srem('selected_%s' % user.id, sku_id)
            return JsonResponse({'code': 0, 'errmsg': 'ok'})
        else:
            cookie_carts = request.COOKIES.get('carts')
            if cookie_carts:
                carts = pickle.loads(base64.b64decode(cookie_carts))
            else:
                carts = {}
            del carts[sku_id]
            new_carts = base64.b64encode(pickle.dumps(carts))
            response = JsonResponse({'code': 0, 'errmsg': 'ok'})
            response.set_cookie('carts', new_carts.decode(), max_age=14 * 24 * 3600)

            return response
