"""
1、您的自定义存储系统必须是子类 django.core.files.storage.Storage
2、Django必须能够在没有任何参数的情况下实例化您的存储系统
    我们在创建存储类的时候，不传递任何参数
3、您的存储类必须实现_open()和_save()方法，以及适用于您的存储类的任何其它方法url
"""

from django.core.files.storage import Storage


class MyStorage(Storage):

    def _open(self, name, mode='rb'):
        pass

    def _save(self, name, content, max_length=None):
        pass

    def url(self, name):
        return "http://192.168.19.128:8888/" + name
