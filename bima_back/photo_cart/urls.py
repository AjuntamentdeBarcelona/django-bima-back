# -*- coding: utf-8 -*-

from django.conf.urls import url
from .views import AddPhotoCart, RemovePhotoCart, RemoveMultiplePhotoCart

urlpatterns = [
    url(r'^add/(?P<pk>[0-9]+)/$', AddPhotoCart.as_view(), name='cart_add'),
    url(r'^remove/$', RemoveMultiplePhotoCart.as_view(), name='cart_remove'),
    url(r'^remove/(?P<pk>[0-9]+)/$', RemovePhotoCart.as_view(), name='cart_remove'),
]
