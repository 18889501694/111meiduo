#!/usr/bin/env python

# ../当前目录的上一级目录，也就是base_dir

"""详情页面的静态化脚本"""
import sys
import os
import django

from apps.goods.models import SKU
from utils.goods import get_breadcrumb, get_categories, get_goods_specs

sys.path.insert(0, '.../')

# 告诉os我们的django的配置文件在哪里
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meiduo_mall.settings')

# django setup
# 相当于 当前的文件 有了django 在django环境下执行
django.setup()


def generic_detail_html(sku):
    # try:
    #     sku = SKU.objects.get(id=sku_id)
    # except SKU.DoesNotExist:
    #     pass
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
    # 加载模板
    from django.template import loader
    detail_template = loader.get_template('detail.html')

    # 模板渲染
    detail_html_data = detail_template.render(context)
    # 写入到指定文件
    import os
    from meiduo_mall import settings
    file_path = os.path.join(os.path.dirname(settings.BASE_DIR), 'front_end_pc/goods/%s.html' % sku.id)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(detail_html_data)

    print(sku.id)


skus = SKU.objects.all()
for sku in skus:
    generic_detail_html(sku)
