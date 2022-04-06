"""定时任务"""
import time

from apps.contents.models import ContentCategory
from utils.goods import get_categories


def generic_meiduo_index(self):
    """页面静态化"""
    print('---%s----' % time.ctime())
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
    # 加载渲染模板
    from django.template import loader
    index_template = loader.get_template('index.html')

    # 把数据给模板
    index_html_data = index_template.render(context)
    # 把渲染好的HTML,写入到指定文件
    from meiduo_mall import settings
    import os
    # base_dir的上一级
    file_path = os.path.join(os.path.dirname(settings.BASE_DIR), 'front_end_pc/index.html')

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(index_html_data)
