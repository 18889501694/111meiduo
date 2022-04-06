from django.urls import converters


# 定义转换器
class UsernameConverter:
    regex = '[a-zA-Z0-9 -]{5,20}'

    def to_python(self, value):
        return value
