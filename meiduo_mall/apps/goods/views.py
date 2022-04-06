# from django.shortcuts import render
# from fdfs_client.client import Fdfs_client
# # 创建客户端，修改加载配置文件的路径
# client = Fdfs_client('utils/fastdfs/client.conf')
#
# # 上传图片，图片的绝对路径
# client.upload_by_filename('\Users\HP\Desktop\符芳窍\img\2.jpg')
#
# # 获取file_id.upload_by_filename上传成功会返回字典数据 ，字典数据中有file_id
import time

from django.shortcuts import render
from django.views import View
from utils.goods import get_categories
from apps.contents.models import ContentCategory

from apps.goods.models import GoodsCategory
from django.http import JsonResponse
from utils.goods import get_breadcrumb, get_goods_specs
from apps.goods.models import SKU
from django.core.paginator import Paginator
from haystack.views import SearchView

from apps.goods.models import GoodsVisitCount
from datetime import date


class IndexView(View):
    """首页广告"""

    def get(self, request):
        """
        首页的数据分为2部分
         1、商品分类数据
         2、广告数据
         3、渲染模板上下文
        """
        categories = get_categories()  # 1
        # 2
        contents = {}
        content_categories = ContentCategory.objects.all()
        for cat in content_categories:
            contents[cat.key] = cat.content_set, filter(status=True).order_by('sequence')

        # 3
        context = {
            'categories': categories,
            'contents': contents,
        }
        return render(request, 'index.html', context)


class ListView(View):
    """商品页面展示"""

    def get(self, request, category_id):
        """
         1、接收参数（排序字段、每页多少条数据、要第几页数据）
         2、获取分类id（）
         3、根据分类id进行分类数据的查询验证
         4、获取面包屑数据
         5、查询分类对应的sku数据，然后排序，再分页（分页、列表数据、每页多少条数据、获取指定页码的数据、将对象转化为字典数据）
            object_list,per_page  object_list列表数据  per_page每页多少条数据
        """
        ordering = request.GET.get('ordering')  # 排序字段
        page_size = request.GET.get('page_size')  # 每页多少条数据
        page = request.GET.get('page')  # 要第几页数据

        try:
            category = GoodsCategory.objects.get(id=category_id)  # 获取分类id
        except GoodsCategory.DoesNotExist:  # 根据分类id进行分类数据的查询验证
            return JsonResponse({'code': 400, 'errmsg': '参数缺失'})
        # 获取面包屑数据
        breadcrumb = get_breadcrumb(category)
        # 查询分类对应的sku数据，然后排序，再分页
        skus = SKU.objects.filter(category=category, is_launched=True).order_by(ordering)
        # 分页
        paginator = Paginator(skus, per_page=page_size)
        # 获取指定页码的数据
        page_skus = paginator.page(page)
        # 列表数据
        sku_list = []
        # 将对象转化为字典数据
        for sku in page_skus.object_list:
            sku_list.append({
                'id': sku.id,
                'name': sku.name,
                'price': sku.price,
                'default_image_url': sku.default_image.url
            })
            # 获取总页码
            total_num = paginator.num_pages

            return JsonResponse({
                'code': 0,
                'errmsg': 'ok',
                'list': sku_list,
                'count': total_num,
                'breadcrumb': breadcrumb
            })


class SKUSearchView(SearchView):
    """商品搜索"""

    def create_response(self):
        # 获取搜索结果，如何知道里面有什么数据？添加断点--结果是list 遍历
        context = self.get_context()
        sku_list = []
        for sku in context['page'].object_list:
            sku_list.append({
                'id': sku.object.id,
                'name': sku.object.name,
                'price': sku.object.price,
                'default_image_url': sku.object.default_image.url,
                'searchkey': context.get('query'),
                'page_size': context['page'].paginator.num_pages,
                'count': context['page'].paginator.count,
            })

        return JsonResponse(sku_list, safe=False)


class DetailView(View):
    """详情页面"""

    def get(self, request, sku_id):
        """
        需求: 详情页面
        1、分类数据 2、面包屑 3、SKU信息 4、规格信息
        我们的详情页面也是需要静态化实现的。
        但是我们再讲解静态化之前，应该可以先把详情页面的数据展示出来
        """
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            pass
        # 1、分类数据
        categories = get_categories()
        # 2、面包屑
        breadcrumb = get_breadcrumb(sku.category)
        # 3、SKU信息
        # 4、规格信息
        goods_specs = get_goods_specs(sku)
        # 渲染
        context = {
            'categories': categories,
            'breadcrumb': breadcrumb,
            'sku': sku,
            'specs': goods_specs,
        }
        return render(request, 'detail.html', context)


class CategoryVisitCountView(View):
    """分类商品统计实现"""

    def post(self, request, category_id):
        """
            1、接收分类id
            2、验证参数（验证分类id）
            3、查询当天，这个分类的记录有没有
            4、没有记录则新建数据
            5、有的话就更新数据
            6、返回响应
        """
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return JsonResponse({'code': 400, 'errmsg': '没有此分类'})

        today = date.today()
        try:
            gvc = GoodsVisitCount.objects.get(category=category, date=today)
        except GoodsVisitCount.DoesNotExist:
            GoodsVisitCount.objects.create(category=category, date=today, count=1)
        else:
            gvc.count += 1
            gvc.save()

        return JsonResponse({'code': 0, 'errmsg': 'ok'})
