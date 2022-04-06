# 伪代码
# Broker
class Broker(object):
    # 消息队列
    broker_list = []


# Worker
class Worker(object):
    # 任务执行者
    def run(self, broker, func):
        if func in broker.broker_list:
            func()
        else:
            return 'error'


# Celery
class Celery(object):
    def __init__(self):
        self.broker = Broker()
        self.worker = Worker()

    def add(self, func):
        self.broker.broker_list.append(func)

    def work(self, func):
        self.worker.run(self.broker, func)


# Task
def send_sms_code():
    print('send_sms_code')


# 创建celery实例对象
app = Celery()
# 添加任务
app.add(send_sms_code)
# worker执行任务
app.work(send_sms_code)
