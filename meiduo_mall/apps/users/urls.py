from django.urls import path
from apps.users.views import UsernameCountView, RegisterView, LoginView, AddressView
from apps.users.views import LogoutView, CenterView, EmailsView, EmailVerifyView
from apps.users.views import AddressCreateView, UserHistoryView

urlpatterns = [
    path('usernames/<username:username>/count/', UsernameCountView.as_view()),
    path('register/', RegisterView.as_view()),
    path('login/', LoginView.as_view()),
    path('logout/', LogoutView.as_view()),
    path('info/', CenterView.as_view()),
    path('emails/', EmailsView.as_view()),
    path('emails/verification/', EmailVerifyView.as_view()),
    path('addresses/create/', AddressCreateView.as_view()),
    path('address/', AddressView.as_view()),
    path('browse_histories/', UserHistoryView.as_view()),
]
