# -*- coding: utf-8 -*-

from enum import IntEnum, unique
from os.path import join
import six

from coreapi import Client
from coreapi.exceptions import CoreAPIException, ErrorMessage, ParameterError
from coreapi.transports import HTTPTransport
from django.conf import settings
from django.core.cache import cache

from .utils import get_class_name, cache_set, cache_delete_startswith
from .constants import HTTP_BAD_REQUEST, ACTION_VIEW_PHOTO, ACTION_DOWNLOAD_PHOTO, CACHE_USER_PROFILE_PREFIX_KEY, \
    CACHE_SCHEMA_PREFIX_KEY, PRIVATE_API_SCHEMA_URL, PUBLIC_API_SCHEMA_URL


@unique
class UploadStatus(IntEnum):
    """
    Maps Photo.upload_status from bima-core.
    """
    upload_error = 0
    uploading = 1
    uploaded = 2


class ServiceClientException(Exception):
    """
    A base class for all `service client` exceptions.
    """

    def __init__(self, error_code=None, coreapi_error=None):
        self.code_error = error_code or 500
        if isinstance(coreapi_error, six.string_types):
            self.code_text = coreapi_error
        else:
            self.code_text = get_class_name(coreapi_error)
            if coreapi_error and isinstance(coreapi_error, ErrorMessage):
                self.code_text = coreapi_error.error.title


class DAMPublicWebService(object):
    """
    For api requests without token
    """

    def __init__(self, request):
        super(DAMPublicWebService, self).__init__()
        api_url = join(settings.WS_BASE_URL, PUBLIC_API_SCHEMA_URL)

        self.request = request
        self.client = Client()

        self.schema = self.client.get(api_url)

    def password_reset(self, params):
        path_list = ['auth', 'password', 'reset', 'create']
        return self.client.action(self.schema, path_list, params=params)

    def password_reset_confirm(self, params):
        path_list = ['auth', 'password', 'reset', 'confirm', 'create']
        return self.client.action(self.schema, path_list, params=params)


class DAMWebService(object):
    """
    For api requests with token
    """

    def __init__(self, request):
        super(DAMWebService, self).__init__()
        api_url = join(settings.WS_BASE_URL, PRIVATE_API_SCHEMA_URL)

        self.request = request
        self.user_id = request.user.id
        self.language = request.META.get('HTTP_ACCEPT_LANGUAGE', request.LANGUAGE_CODE)

        # initialize api client with user token
        user_params = cache.get("{}_{}".format(CACHE_USER_PROFILE_PREFIX_KEY, self.user_id))
        authorization = {}
        if user_params and user_params.get('token'):
            authorization = {'Authorization': 'Token {}'.format(user_params.get('token'))}
        headers = dict(authorization)
        headers.update({'Accept-Language': self.language})

        transports = HTTPTransport(credentials=authorization, headers=headers,
                                   response_callback=self._callback_client_transport)
        self.client = Client(transports=[transports])

        # get api schema
        schema_cache_key = "{}_{}".format(CACHE_SCHEMA_PREFIX_KEY, self.user_id)
        self.schema = cache.get(schema_cache_key)
        if not self.schema:
            self.schema = self.get_or_logout(api_url)
            cache.set(schema_cache_key, self.schema)

    def get_client_schema(self):
        return self.schema

    def _callback_client_transport(self, response):
        self.transport_status_code = response.status_code

    def get_or_logout(self, url):
        """
        Method to get the schema of the api according the client, which depends of the user who requests.
        Raise a ServiceClientException on error customizing the error code.
        """
        try:
            response = self.client.get(url)
            return response
        except ParameterError as e:
            raise ServiceClientException(HTTP_BAD_REQUEST, e)
        except CoreAPIException as e:
            raise ServiceClientException(self.transport_status_code, e)

    def action_or_logout(self, path_list, params, use_cache=False, clear_cache=False):
        """
        to execute the action
        """

        # get response from cache if use cache is
        if use_cache:
            cache_suffix_key = "_".join(["{}_{}".format(key, params[key]) for key in sorted(params.keys())])
            cache_key = "{}_{}_{}_{}".format("_".join(path_list),
                                             self.language,
                                             self.user_id,
                                             cache_suffix_key)
            response = cache.get(cache_key)
            if response:
                return response

        # do request through api client
        try:
            response = self.client.action(self.schema, path_list, params=params)
            # clear all request related entries in cache
            if clear_cache:
                cache_delete_startswith(path_list[0])
                return response
            # if response successful status code
            if use_cache:
                cache_set(cache_key, response)
            return response
        except ParameterError as e:
            raise ServiceClientException(HTTP_BAD_REQUEST, e)
        except CoreAPIException as e:
            raise ServiceClientException(self.transport_status_code, e)

    # auth

    def password_change(self, params):
        return self.action_or_logout(['auth', 'password', 'change', 'create'], params=params)

    # users

    def get_user_info(self):
        return self.action_or_logout(['whoami', 'list'], {})

    def get_user(self, user_id):
        return self.action_or_logout(['users', 'read'], params={'id': user_id})

    def get_users_list(self, **kwargs):
        return self.action_or_logout(['users', 'list'], params=kwargs)

    def user_create(self, params):
        return self.action_or_logout(['users', 'create'], params=params)

    def user_edit(self, params):
        return self.action_or_logout(['users', 'partial_update'], params=params)

    def delete_user(self, user_id):
        return self.action_or_logout(['users', 'delete'], params={'id': user_id})

    # groups

    def get_groups_list(self, **kwargs):
        return self.action_or_logout(['groups', 'list'], params=kwargs)

    # albums

    def get_albums_simple_list(self, **kwargs):
        """
        Albums list with only 'id', 'title' and 'description information
        """
        return self.action_or_logout(['albums', 'flat', 'list'], params=kwargs)

    def get_albums_list(self, **kwargs):
        return self.action_or_logout(['albums', 'list'], params=kwargs)

    def get_album(self, album_id):
        return self.action_or_logout(['albums', 'read'], params={'id': album_id})

    def create_album(self, params):
        return self.action_or_logout(['albums', 'create'], params)

    def update_album(self, params):
        return self.action_or_logout(['albums', 'partial_update'], params)

    def delete_album(self, album_id):
        return self.action_or_logout(['albums', 'delete'], params={'id': album_id})

    # photos

    def search_photos_list(self, **kwargs):
        return self.action_or_logout(['search', 'list'], params=kwargs)

    def get_photos_list(self, **kwargs):
        return self.action_or_logout(['photos', 'list'], params=kwargs)

    def get_photo(self, photo_id):
        return self.action_or_logout(['photos', 'read'], params={'id': photo_id})

    def create_photo(self, params):
        return self.action_or_logout(['photos', 'create'], params=params)

    def update_photo(self, params):
        return self.action_or_logout(['photos', 'partial_update'], params)

    def update_photo_multiple(self, params):
        return self.action_or_logout(['photos', 'addition', 'partial_update'], params)

    def delete_photo(self, photo_id):
        return self.action_or_logout(['photos', 'delete'], params={'id': photo_id})

    # youtube

    def youtube_channels(self, photo_pk):
        return self.action_or_logout(['photos', 'youtube', 'list'], params={'id': photo_pk})

    def youtube_upload(self, photo_pk, youtube_channel_pk):
        return self.action_or_logout(['photos', 'youtube', 'create'], params={
            'id': photo_pk, 'channel_pk': youtube_channel_pk})

    # vimeo

    def vimeo_accounts(self, photo_pk):
        return self.action_or_logout(['photos', 'vimeo', 'list'], params={'id': photo_pk})

    def vimeo_upload(self, photo_pk, vimeo_account_pk):
        return self.action_or_logout(['photos', 'vimeo', 'create'], params={
            'id': photo_pk, 'account_pk': vimeo_account_pk})

    # galleries

    def get_galleries_simple_list(self, **kwargs):
        """
        Galleries list with only 'id', 'title' and 'description' information
        """
        return self.action_or_logout(['galleries', 'flat', 'list'], params=kwargs)

    def get_galleries_list(self, **kwargs):
        return self.action_or_logout(['galleries', 'list'], params=kwargs)

    def get_gallery(self, gallery_id):
        return self.action_or_logout(['galleries', 'read'], params={'id': gallery_id})

    def create_gallery(self, params):
        return self.action_or_logout(['galleries', 'create'], params=params)

    def update_gallery(self, params):
        return self.action_or_logout(['galleries', 'partial_update'], params)

    def delete_gallery(self, gallery_id):
        return self.action_or_logout(['galleries', 'delete'], params={'id': gallery_id})

    # categories

    def get_categories_simple_list(self, **kwargs):
        """
        Categories list with only 'id' and 'title' information
        """
        return self.action_or_logout(['categories', 'flat', 'list'], params=kwargs, use_cache=True)

    def get_categories_list(self, **kwargs):
        return self.action_or_logout(['categories', 'list'], params=kwargs, use_cache=True)

    def get_categories_level_list(self, **kwargs):
        """
        Like get_categories_list but only for one level, not the entire tree.
        """
        return self.action_or_logout(['categories-level', 'list'], params=kwargs, use_cache=True)

    def get_category(self, category_id):
        return self.action_or_logout(['categories', 'read'], params={'id': category_id}, use_cache=True)

    def create_category(self, params):
        return self.action_or_logout(['categories', 'create'], params=params, clear_cache=True)

    def update_category(self, params):
        return self.action_or_logout(['categories', 'update'], params, clear_cache=True)

    def delete_category(self, category_id):
        return self.action_or_logout(['categories', 'delete'], params={'id': category_id}, clear_cache=True)

    # metadata

    def get_names_list(self, **kwargs):
        """
        Tag-Name list filtered by a part of its content
        """
        return self.action_or_logout(['names', 'list'], params=kwargs)

    def get_keywords_list(self, **kwargs):
        """
        Tag-Name list filtered by a part of its content
        """
        return self.action_or_logout(['keywords', 'list'], params=kwargs)

    # copyrights

    def get_authors_list(self, **kwargs):
        """
        Photo author list filtered by a part of its name
        """
        return self.action_or_logout(['authors', 'list'], params=kwargs)

    def get_copyrights_list(self, **kwargs):
        """
        Copyright list filtered by a part of its name
        """
        return self.action_or_logout(['copyrights', 'list'], params=kwargs)

    def get_restrictions_list(self, **kwargs):
        """
        Restriction list filtered by a part of its title
        """
        return self.action_or_logout(['restrictions', 'list'], params=kwargs)

    # link

    def create_link(self, params):
        return self.action_or_logout(['link', 'create'], params=params)

    def delete_link(self, params):
        return self.action_or_logout(['link', 'delete'], params=params)

    # logger

    def logger_view(self, params):
        params['action'] = ACTION_VIEW_PHOTO
        return self.logger_action(params)

    def logger_download(self, params):
        params['action'] = ACTION_DOWNLOAD_PHOTO
        return self.logger_action(params)

    def logger_action(self, params):
        return self.action_or_logout(['logger', 'create'], params=params)

    def get_log_list(self, **kwargs):
        return self.action_or_logout(['logger', 'list'], params=kwargs)

    def get_photo_upload_log_list(self, **kwargs):
        return self.action_or_logout(['photos', 'upload', 'list'], params=kwargs)

    # exports

    def export_logger(self, kwargs):
        return self.action_or_logout(['exports', 'logger', 'list'], params=kwargs)

    # flickr

    def flickr_import(self, params):
        return self.action_or_logout(['photos', 'import', 'album', 'create'], params=params)

    # photo type

    def get_photo_type_list(self, **params):
        return self.action_or_logout(['types', 'list'], params=params)
