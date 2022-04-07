from django.core.cache import cache
from django.views import View
from apps.areas.models import Area
from django.http import JsonResponse


class AreaView(View):

    def get(self, request):
        """
        优化
        0.先看缓存有没有数据，如果有就直接返回json，没有的话就进行if判断查询
        1.查询省份信息（查询结果集）
        2.将对象转换为字典数据（对象不能直接返回json，要先转成字典）
        3.设置缓存cache
        4.返回响应
        """
        province_list = cache.get('province')
        if province_list is None:
            provinces = Area.objects.filter(parent=None)
            province_list = []
            for province in provinces:
                province_list.append({'id': province.id, 'name': province.name})
            cache.set('province', province_list, 24 * 3600)

        return JsonResponse({'code': 0, 'errmsg': 'ok', 'province_list': province_list})


class SubAreaView(View):

    def get(self, request):
        """
        1.获取省份id，市县的id，查询信息（Area.objects.filter(parent_id=id  Area.objects.filter(parent_id=id）
        2.将对象转换成字典数据
        3.设置缓存cache
        4.返回响应
        """
        data_list = cache.get('city')
        if data_list is None:
            up_level = Area.objects.get(id=id)
            down_level = up_level.subs.all()
            data_list = []
            for item in down_level:
                data_list.append({'id': item.id, 'name': item.name, })
            cache.set('city:%s' % id, data_list, 24 * 3600)

        return JsonResponse({'code': 0, 'errmsg': 'ok', 'sub_data': {'subs': data_list}})
