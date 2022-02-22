# -*- coding: utf-8 -*-
import logging
from os.path import join

from constance import config
from coreapi import Client
from coreapi.transports import HTTPTransport
from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django_rq import job

from .utils import cache_set
from .constants import CACHE_SCHEMA_PREFIX_KEY, PRIVATE_API_SCHEMA_URL
from .models import MyChunkedUpload

BOUNDARY = 'BoUnDaRyStRiNg'
MULTIPART_CONTENT = 'multipart/form-data; boundary=%s' % BOUNDARY


logger = logging.getLogger(__name__)


def _checksum_file(file, chunk_size):
    from hashlib import md5
    checksum = md5()
    for chunk in file.chunks(chunk_size):
        checksum.update(chunk)
    return checksum.hexdigest()


@job('back', timeout=settings.JOB_DEFAULT_TIMEOUT)
def upload_photo(form_data, user_id, user_token, lang, create=True):
    try:
        api_url = join(settings.WS_BASE_URL, PRIVATE_API_SCHEMA_URL)
        chunk_size = config.PHOTO_UPLOAD_CHUNK_SIZE

        # request headers
        token_header = 'Token'
        if hasattr(settings, 'IS_OAUTH_AUTH') and settings.IS_OAUTH_AUTH:
            token_header = 'Bearer'
        authorization = {'Authorization': '{} {}'.format(token_header, user_token)}
        headers = dict(authorization)
        headers.update({'Accept-Language': lang, 'content_type': MULTIPART_CONTENT})

        transports = HTTPTransport(credentials=authorization, headers=headers)
        client = Client(transports=[transports])

        # get api schema
        schema_cache_key = "{}_{}".format(CACHE_SCHEMA_PREFIX_KEY, user_id)
        schema = cache.get(schema_cache_key)
        if not schema:
            schema = client.get(api_url)
            cache_set(schema_cache_key, schema)

        # get image to upload
        upload_id = form_data.pop('upload_id')
        image = MyChunkedUpload.objects.get(upload_id=upload_id)
        image_file = image.file
        filename = image.filename

        # request parameters
        data = {'filename': filename}
        offset, chunks = 0, image_file.chunks(chunk_size)
        request_path = ['photos', 'upload', 'update']
        img_id = 0

        for chunk_file in chunks:
            data.update(**{'file': ContentFile(chunk_file)})
            client.transports[0].headers._data['Content-Range'] = 'bytes {}-{}/{}'.format(
                offset, offset + len(chunk_file) -1, image_file.size)
            response = client.action(schema, request_path, params=data)
            offset = response['offset']
            img_id = response['id']
            data.update({'id': img_id})
            request_path = ['photos', 'upload', 'chunk', 'update']

        request_path = ['photos', 'upload', 'chunk', 'create']
        data.update({'md5': _checksum_file(image_file, chunk_size)})
        client.action(schema, request_path, params=data)

        # Request is not multipart, so we remove the header, otherwise uwsgi doesn't works
        client.transports[0].headers._data.pop('content_type', None)

        # upload photo information
        form_data['image'] = img_id
        form_data['original_file_name'] = filename
        if create:
            form_data['owner'] = user_id
            client.action(schema, ['photos', 'create'], params=form_data)
        else:
            client.action(schema, ['photos', 'partial_update'], params=form_data)
    except Exception:
        logger.exception('Unexpected exception in upload_photo task')
