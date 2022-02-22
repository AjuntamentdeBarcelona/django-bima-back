# -*- coding: utf-8 -*-
import logging
from os.path import join

from constance import config
import coreapi
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import PermissionDenied

from .utils import cache_set
from .constants import CACHE_USER_PROFILE_PREFIX_KEY, PRIVATE_API_SCHEMA_URL


logger = logging.getLogger(__name__)


class WSAuthenticationBackend(object):
    """
    To authenticate user through api is required a installed cache backend to store temporally the user data.
    Otherwise system will not authenticate.
    """

    def authenticate(self, request, **kwargs):
        """
        Authentication through API request using coreapi.
        :param username:
        :param password:
        :return: user instance
        """
        username = kwargs.get('username')
        password = kwargs.get('password')
        # initialize client
        client = coreapi.Client()
        api_url = join(settings.WS_BASE_URL, PRIVATE_API_SCHEMA_URL)
        schema = client.get(api_url)

        # get user token
        params = {'username': username, 'password': password}
        try:
            token = client.action(schema, ['api-token-auth', 'create'], params=params)['token']
        except (coreapi.exceptions.ErrorMessage, KeyError):
            raise PermissionDenied()

        # initialize client with token
        authorization = {'Authorization': 'Token {}'.format(token)}
        transports = coreapi.transports.HTTPTransport(credentials=authorization, headers=authorization)
        client = coreapi.Client(transports=[transports])
        schema = client.get(api_url)

        # get user data and save it in cache
        user_data = client.action(schema, ['whoami', 'read'])
        is_superuser = config.ADMIN_ID in user_data['groups'] or user_data['is_superuser']
        user_params = {
            'id': user_data['id'],
            'username': user_data['username'],
            'first_name': user_data['first_name'],
            'last_name': user_data['last_name'],
            'email': user_data['email'],
            'dam_groups': user_data['groups'],
            'token': token,
            'admin': is_superuser,
            'is_staff': is_superuser,
            'is_superuser': is_superuser,
            'permissions': user_data['permissions'],
        }
        # store into cache the new user info
        cache_set("{}_{}".format(CACHE_USER_PROFILE_PREFIX_KEY, user_data['id']), user_params)
        logger.debug(user_data['permissions'])

        # user model
        user_model = get_user_model()
        if user_params['is_staff']:
            # save superusers in order to let them do actions in the admin site
            # that need to register the log, for example, deleting a chunkedupload object
            user_model.objects.update_or_create(
                id=user_params['id'],
                defaults={
                    'username': user_params['username'],
                    'is_staff': user_params['is_staff'],
                    'admin': user_params['admin'],
                    'is_superuser': user_params['is_superuser'],
                }
            )
        return user_model(**user_params)

    def get_user(self, user_id):
        """
        Get the user information from cache
        :param user_id:
        :return: user instance
        """
        user_params = cache.get("{}_{}".format(CACHE_USER_PROFILE_PREFIX_KEY, user_id))
        if user_params:
            cache_set("{}_{}".format(CACHE_USER_PROFILE_PREFIX_KEY, user_params['id']), user_params)
            return get_user_model()(**user_params)
        return None

    def __init__(self, session_key=None):
        super(WSAuthenticationBackend, self).__init__()
