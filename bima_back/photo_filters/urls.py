# -*- coding: utf-8 -*-

from django.conf.urls import url
from .views import AddFilter, RemoveFilter

urlpatterns = [
    url(r'^add/$', AddFilter.as_view(), name='filter_add'),
    url(r'^remove/(?P<pk>[0-9]+)/$', RemoveFilter.as_view(), name='filter_remove'),
]
