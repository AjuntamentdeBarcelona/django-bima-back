# -*- coding: utf-8 -*-
from django.conf.urls import url, include

from . import views

urlpatterns = [

    url(r'^$', views.PhotoListView.as_view(), name='home'),
    url(r'^search/', include('bima_back.autocomplete.urls')),
    url(r'^cart/', include('bima_back.photo_cart.urls')),
    url(r'^filters/', include('bima_back.photo_filters.urls')),

    # my photos
    url(r'^my-photos/$', views.MyPhotosListView.as_view(), name='my_photos_list'),

    # albums
    url(r'^album/$', views.AlbumListView.as_view(), name='album_list'),
    url(r'^album/public/$', views.AlbumPublicListView.as_view(), name='album_public_list'),
    url(r'^album/create/$', views.AlbumCreateView.as_view(), name='album_create'),
    url(r'^album/edit/(?P<pk>[0-9]+)/$', views.AlbumEditView.as_view(), name='album_edit'),
    url(r'^album/edit/(?P<pk>[0-9]+)/cover/(?P<cover>[0-9]+)/$', views.AlbumCoverView.as_view(), name='album_cover'),
    url(r'^album/detail/(?P<pk>[0-9]+)/$', views.AlbumDetailView.as_view(), name='album_detail'),
    url(r'^album/delete/(?P<pk>[0-9]+)/$', views.AlbumDeleteView.as_view(), name='album_delete'),

    # photos
    url(r'^photo/$', views.PhotoListView.as_view(), name='photo_list'),
    url(r'^photo/create/$', views.PhotoCreateMultipleView.as_view(), name='photo_create'),
    url(r'^photo/create/flickr/$', views.FlickrImportView.as_view(), name='photo_create_flickr'),
    # upload photo to a preselected album
    url(r'^photo/create/album/(?P<album>[0-9]+)/$', views.AlbumPhotoCreateMultipleView.as_view(),
        name='photo_create'),
    url(r'^photo/create/flickr/album/(?P<album>[0-9]+)/$', views.AlbumFlickrImportView.as_view(),
        name='photo_create_flickr'),
    url(r'^photo/edit/(?P<pk>[0-9]+)/$', views.PhotoEditView.as_view(), name='photo_edit'),
    url(r'^photo/edit/(?P<pk>[0-9]+)/youtube/$', views.PhotoEditYoutubeView.as_view(), name='photo_edit_youtube'),
    url(r'^photo/edit/(?P<pk>[0-9]+)/vimeo/$', views.PhotoEditVimeoView.as_view(), name='photo_edit_vimeo'),
    url(r'^photo/edit/multiple/$', views.PhotoEditMultipleView.as_view(), name='photo_edit_multiple'),
    url(r'^photo/delete/(?P<pk>[0-9]+)/$', views.PhotoDeleteView.as_view(), name='photo_delete'),
    url(r'^photo/detail/(?P<pk>[0-9]+)/$', views.PhotoDetailView.as_view(), name='photo_detail'),
    url(r'^photo/copy-tags/(?P<pk>[0-9]+)/$', views.PhotoEditTagsRedirectView.as_view(), name='photo_copy_tags'),
    url(r'^photo/download/(?P<pk>[0-9]+)/$', views.PhotoDownloadLogView.as_view(), name='photo_download_log'),

    # photo chunked upload
    url(r'^api/chunked_upload/$', views.PhotoChunkedUploadView.as_view(), name='api_chunked_upload'),
    url(r'^api/chunked_upload_complete/$', views.PhotoChunkedUploadCompleteView.as_view(),
        name='api_chunked_upload_complete'),

    # galleries
    url(r'^gallery/$', views.GalleryListView.as_view(), name='gallery_list'),
    url(r'^gallery/create/$', views.GalleryCreateView.as_view(), name='gallery_create'),
    url(r'^gallery/edit/(?P<pk>[0-9]+)/$', views.GalleryEditView.as_view(), name='gallery_edit'),
    url(r'^gallery/edit/(?P<pk>[0-9]+)/cover/(?P<cover>[0-9]+)/$', views.GalleryCoverView.as_view(),
        name='gallery_cover'),
    url(r'^gallery/detail/(?P<pk>[0-9]+)/$', views.GalleryDetailView.as_view(), name='gallery_detail'),
    url(r'^gallery/delete/(?P<pk>[0-9]+)/$', views.GalleryDeleteView.as_view(), name='gallery_delete'),

    # categories
    url(r'^category/$', views.CategoryListView.as_view(), name='category_list'),
    url(r'^category/create/$', views.CategoryCreateView.as_view(), name='category_create'),
    url(r'^category/edit/(?P<pk>[0-9]+)/$', views.CategoryEditView.as_view(), name='category_edit'),
    url(r'^category/delete/(?P<pk>[0-9]+)/$', views.CategoryDeleteView.as_view(), name='category_delete'),
    url(r'^category/children/$', views.CategoryChildrenAjaxListView.as_view(),
        name='category_children_list'),

    # users
    url(r'^user/create/$', views.UserCreateView.as_view(), name='user_create'),
    url(r'^user/manage/$', views.UserManageView.as_view(), name='user_manage'),
    url(r'^user/manage/(?P<pk>[0-9]+)/$', views.UserEditView.as_view(), name='user_edit'),
    url(r'^user/manage/(?P<pk>[0-9]+)/delete/$', views.UserDeleteView.as_view(), name='user_delete'),
    url(r'^user/manage/(?P<pk>[0-9]+)/active/$', views.UserActiveView.as_view(), name='user_active'),

    # logs
    url(r'^photo/log/$', views.LogListView.as_view(), name='log_list'),
    url(r'^photo/upload/log/$', views.PhotoUploadListView.as_view(), name='photo_log_list'),

]

handler403 = 'django.views.defaults.permission_denied'
handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'
