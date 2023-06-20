from django.urls import path
from .views import add_coupon

app_name = 'coupon'

urlpattern = [
    path('add/', add_coupon, name='add'),
]