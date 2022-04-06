'''
生产者 消费者 队列 Celery
'''
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meiduo_mall.settings')

# 创建celery实例,通过加载配置文件来设置broker
app = Celery('celery_tasks')

# 设置broker
app.config_from_object('celery_tasks.config')

# 需要celery自动检测指定包的任务，autodiscover_tasks参数是列表，列表中的元素是tasks的路径
app.autodiscover_tasks(['celery_tasks.sms', 'celery_tasks.email'])
