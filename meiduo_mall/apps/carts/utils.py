import base64
import pickle

from django_redis import get_redis_connection


def merge_cookie_to_redis(request, response):
    """
    1、读取cookie数据
    2、初始化一个字典 用于保存sku_id:count
        初始化一个列表 用于保存选中的商品id
        初始化一个列表 用于保存未选中的商品id
    3、遍历cookie数据
            {
                1:{count:6666,selected:True},
                2:{count:9999,selected:True},
                5:{count:9999,selected:False},
            }
    4、将字典数据，列表数据分别添加到redis中
    5、删除cookie数据
    """
    cookie_carts = request.COOKIES.get('carts')
    if cookie_carts:
        carts = pickle.loads(base64.b64decode(cookie_carts))

    cookie_dict = {}
    selected_ids = []
    unselected_ids = []

    for sku_id, count_selected_dict in carts.item():
        cookie_dict[sku_id] = count_selected_dict['count']  # 字典数据
        if count_selected_dict['selected']:
            selected_ids.append(sku_id)
        else:
            unselected_ids.append(sku_id)

    user = request.user
    redis_cli = get_redis_connection('carts')
    pipeline = redis_cli.pipeline()  # 管道
    pipeline.hmest('carts_%s' % user.id, cookie_dict)
    if len(selected_ids) > 0:
        pipeline.sadd('selected_%s' % user.id, *selected_ids)  # *selected_ids对列表进行解包

    pipeline.execute()  # 执行管道
    response.delete_cookie('carts')

    return response
