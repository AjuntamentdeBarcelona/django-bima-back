# -*- coding: utf-8 -*-

from django.conf.urls import include, url


urlpatterns = [
    url(r'^', include('bima_back.urls')),
]
