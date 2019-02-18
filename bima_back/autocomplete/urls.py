# -*- coding: utf-8 -*-
from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^group/$', views.GroupSearchView.as_view(), name='group_search'),
    url(r'^user/$', views.UserSearchView.as_view(), name='user_search'),
    url(r'^album/$', views.AlbumSearchView.as_view(), name='album_search'),
    url(r'^photo/$', views.PhotoSearchView.as_view(), name='photo_search'),
    url(r'^category/$', views.CategorySearchView.as_view(), name='category_search'),
    url(r'^gallery/$', views.GallerySearchView.as_view(), name='gallery_search'),
    url(r'^name/$', views.NameSearchView.as_view(), name='name_search'),
    url(r'^keyword/$', views.KeywordSearchView.as_view(), name='keyword_search'),
    url(r'^author/$', views.AuthorSearchView.as_view(), name='author_search'),
    url(r'^copyright/$', views.CopyrightSearchView.as_view(), name='copyright_search'),
    url(r'^restriction/$', views.RestrictionSearchView.as_view(), name='restriction_search'),
    url(r'^type/$', views.TypeSearchView.as_view(), name='type_search'),
]
