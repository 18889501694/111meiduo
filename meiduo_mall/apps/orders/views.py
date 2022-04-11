import json

from django.http import JsonResponse
from django.views import View
from django_redis import get_redis_connection
from django.db import transaction

from apps.goods.models import SKU
from apps.orders.models import OrderInfo
from utils.views import LoginRequiredJSONMixin
from apps.users.models import Address


class OrderSettlementView(View):
    """提交订单页面展示"""

    def get(self, request):
        """
        1、接收用户信息    2、地址信息（1、查询用户的地址信息[Address,Address,....] 2、将对象数据转换为字典数据）
        3、购物车中选中商品的信息（1、连接redis 2、hash 3、set 4、重新组织一个选中的信息 5、根据商品的id查询商品的具体信息[SKU,SKU,。。]）
        """
        user = request.user
        addresses = Address.objects.filter(is_deleted=False)
        addresses_list = []
        for address in addresses:
            addresses_list.append({
                'id': address.id,
                'province': address.province.name,
                'city': address.city.name,
                'district': address.district.name,
                'place': address.receiver,
                'receiver': address.receiver,
                'mobile': address.mobile,
            })

        redis_cli = get_redis_connection('carts')
        pipeline = redis_cli.pipeline()
        pipeline.hegetall('carts_%s' % user.id)
        pipeline.smembers('selected_%s' % user.id)
        result = pipeline.execute()  # result=[hash结果,set结果]
        sku_id_counts = result[0]  # {sku_id:count,sku_id:count}
        selected_ids = result[1]  # [1,2]

        selected_carts = {}  # selected_carts={sku_id:count}
        for sku_id in selected_ids:
            selected_carts[int(sku_id)] = int(sku_id_counts[sku_id])

        sku_list = []
        for sku_id, count in selected_carts.items():
            sku = SKU.objects.get(pk=sku_id)
            sku_list.append({
                'id': sku.id,
                'name': sku.name,
                'count': count,
                'default_image_url': sku.default_image.url,
                'price': sku.price
            })

        from decimal import Decimal
        freight = Decimal('10')
        context = {
            'skus': sku_list,
            'addresses': addresses_list,
            'freight': freight,  # 运费
        }
        return JsonResponse({'code': 0, 'errmsg': 'ok', 'context': context})


class OrderCommitView(LoginRequiredJSONMixin, View):
    """订单基本信息保存"""

    def post(self, request):
        """
         1、接收请求     2、验证数据      3.数据入库（先入订单基本信息，  再入订单商品信息）      3.2获取hash       3.3获取set
         3.4遍历选中商品的id，最好重写组织一个数据·这个数据是选中的商品信息{sku_id:count , sku_id;count}
         3.5遍历根据选中商品的id进行查询
         3.6判断库存是否充足
         3.7如果不充足·下单失败
         3.8如果充足，则库存减少﹐销量增加
         3.9累加总和总金额
         3.10保存订单商品信息
         4.更新订单的总金额和总敦量
         5.将redis中选中的商品信息移除出去
         6、返回响应
        """
        user = request.user
        data = json.loads(request.body.decode())
        address_id = data.get('address_id')
        pay_method = data.get('pay_method')

        if not all([address_id, pay_method]):
            return JsonResponse({'code': 400, 'errmsg': '参数不全'})

        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            return JsonResponse({'code': 400, 'errmsg': '参数不正确'})

        # 提高代码可读性
        if pay_method not in [OrderInfo.PAY_METHODS_ENUM['CASH'], OrderInfo.PAY_METHODS_ENUM['ALIPAY']]:
            return JsonResponse({'code': 400, 'errmsg': '参数不正确'})

        from django.utils import timezone
        from datetime import datetime

        order_id = timezone.localtime().strftime('%Y%m%d%H%M%S') + user  # 时间格式化
        # 支付状态由支付方式决定
        if pay_method == OrderInfo.PAY_METHODS_ENUM['CASH']:
            status = OrderInfo.ORDER_STATUS_ENUM['UNSEND']
        else:
            status = OrderInfo.ORDER_STATUS_ENUM['UNPAID']

        from decimal import Decimal
        total_count = 0
        total_amount = Decimal('0')  # 总金额
        freight = Decimal('10.00')

        with transaction.atomic():
            point = transaction.savepoint()  # 事务开始点（回滚点）

            # 数据入库，生成订单(订单基本信息表和订单商品信息表)
            # 先保存订单基本信息
            orderinfo = OrderInfo.objects.create(
                order_id=order_id,
                user=user,
                address=address,
                total_count=total_amount,
                total_amount=total_amount,
                freight=freight,
                pay_method=pay_method,
                status=status,
            )

            redis_cli = get_redis_connection('carts')
            sku_id_counts = redis_cli.hgetall('carts_%s' % user.id)
            selected_ids = redis_cli.smembers('selected_%s' % user.id)
            carts = {}

            for sku_id in selected_ids:
                carts[int(sku_id)] = int(sku_id_counts[sku_id])

            for sku_id, count in carts.items():
                # for i in range(10): 优化乐观锁
                sku = SKU.objects.get(id=sku_id)

                if sku.stock < count:
                    # 回滚点
                    transaction.savepoint_rollback(point)
                    return JsonResponse({'code': 400, 'errmsg': '库存不足'})

                from time import sleep
                sleep(7)
                # sku.stock -= count
                # sku.sales += count
                # sku.save()

                # -----乐观锁解决超卖问题------
                old_stock = sku.stock  # 旧库存
                new_stock = sku.stock - count
                new_sales = sku.sales + count
                result = SKU.objects.filter(id=sku_id, stock=old_stock).update(stock=new_stock, sales=new_sales)

                # 如果result=1表示有1条记录修改成功，result=0 表示没有更新
                if result == 0:
                    # sleep(0.005) 优化乐观锁
                    continue
                    # # 暂时回滚和返回下单失败
                    # transaction.savepoint_rollback(point)
                    # return JsonResponse({'code': 400, 'errmsg': '下单失败-------'})

                orderinfo.total_count += cout
                orderinfo.total_amount += (count * sku.price)

                from apps.orders.models import OrderGoods
                OrderGoods.objects.create(
                    order=orderinfo,
                    sku=sku,
                    count=count,
                    price=sku.price,
                )
            orderinfo.save()
            transaction.savepoint_commit(point)
        return JsonResponse({'code': 0, 'errmsg': 'ok', 'order_id': order_id})
