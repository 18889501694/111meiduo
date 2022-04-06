from django.urls import path
from apps.goods.views import IndexView, ListView, SKUSearchView, DetailView
from apps.goods.views import CategoryVisitCountView

urlpatterns = [
    path('index/', IndexView.as_view()),
    path('list/category_id/skus/', ListView.as_view()),
    path('search/', SKUSearchView()),  # 直接实例化
    path('detail/<sku_id>/', DetailView.as_view()),
    path('detail/visit/<category_id>/', CategoryVisitCountView()),
]
