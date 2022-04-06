from apps.goods.models import SKU
from haystack import indexes

'''
1、我们需要在模型所对应的子应用中创建search_indexes.py文件，以方便haystack来检索
2、索引类必须继承自indexes.SearchIndex,indexes.Indexable
3、必须定义一个字段 document=True
    字段名 起什么都可以，text只是惯例
    所有的索引的 这个字段 都一致就行
4、use_template=True
    允许我们来单独设置一个文件，来指定哪些字段进行检索
    模板文件夹下/search/indexes/子应用名目录/模型类名小写_text.text
    
数据      《------Haystack----->  elasticsearch
运作：我们应该让haystack 将数据获取到 给es 来生成索引
    python manage.py rebuild_index
    
    借助haystack来对接elasticsearch
    所以haystack可以帮助我们查询数据
'''


class SKUIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)

    def get_model(self):
        # 返回建立索引的模型类
        return SKU

    def index_queryset(self, using=None):
        # 返回要建立索引的数据查询集
        return self.get_model().objects.all()

