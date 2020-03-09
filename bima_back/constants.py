# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _


# Constance config

DEFAULT_CONSTANCE = {
    'GOOGLE_ANALYTICS_TRACKING_CODE': ('UA-XXXXX-Y', 'Google Analytics tracking code.'),
    'ADMIN_ID': (1, 'ID of admin role'),
    'AUTOCOMPLETE_PAGE_SIZE': (10, 'Max results of any autocomplete search.'),
    'AUTOCOMPLETE_PAGE_ITERATION': (3, 'Iterations to get data without warning.'),
    'PHOTO_UPLOAD_CHUNK_SIZE': (100000, 'Chunk bytes when uploading a photo'),
    'MAX_EDIT_MULTIPLE': (10, 'Maximum number of photos that can be edited at the same time'),
    'CHANGE_USER_PASSWORD_URL': ('', 'Url to change a user password.'),
    'RESET_USER_PASSWORD_URL': ('', 'Url to reset a user password.'),
    'REMEMBER_USER_URL': ('', 'Url to remember a user in ldap.'),
    'FOOTER_TEXT': ('', 'Text to display on the footer.'),
    'MAX_FILE_SIZE': (100, 'Maximum file size allowed to upload, in MB.'),
    'MAX_PHOTO_FILE_SIZE': (0, 'Maximum photo file size allowed to upload, in MB. (0 means no special limitation.)'),
}

# http code status
HTTP_BAD_REQUEST = 400

# config autocomplete forms
AUTOCOMPLETE_DEFAULT_MIN_LENGTH = 0


BLANK_OPTION = ('', _('All'))
BLANK_CHOICES = [BLANK_OPTION, ]

# code actions to log
ACTION_VIEW_PHOTO = 0       # Mapping code for view photo action
ACTION_DOWNLOAD_PHOTO = 1   # Mapping code for download photo action
LOG_ACTIONS = [
    (ACTION_VIEW_PHOTO, _('Viewed')),
    (ACTION_DOWNLOAD_PHOTO, _('Downloaded')),
]

# code photo status (privacy)
PHOTO_PRIVATE_STATUS = 0    # Mapping code for private photos
PHOTO_PUBLIC_STATUS = 1     # Mapping code for public photos
PHOTO_STATUS_CHOICES = [
    (PHOTO_PRIVATE_STATUS, _('Private')),
    (PHOTO_PUBLIC_STATUS, _('Public')),
]

# search form tags mappings
LANGUAGE_SEARCH_FORM_TAGS_EN = {
    'identifier': 'identifier',
    'status': 'status',
    'original_file_name': 'original_file_name',
    'internal_comment': 'internal_comment',
    'original_platform': 'original_platform',
    'province': 'province',
    'municipality': 'municipality',
    'district': 'district',
    'neighborhood': 'neighborhood',
    'address': 'address',
    'postcode': 'postcode',
    'width': 'width',
    'height': 'height',
    'camera_model': 'camera_model',
    'flickr_id': 'flickr_id',
    'flickr_username': 'flickr_username',
    'title': 'title',
    'description': 'description',
    'album': 'album',
    'author': 'author',
    'copyright': 'copyright',
    'restriction': 'restriction',
}
LANGUAGE_SEARCH_FORM_TAGS_ES = LANGUAGE_SEARCH_FORM_TAGS_EN
LANGUAGE_SEARCH_FORM_TAGS_CA = {
    'identifier': 'identificador',
    'status': 'estat',
    'original_file_name': 'nom_arxiu_original',
    'internal_comment': 'comentari_intern',
    'original_platform': 'plataforma_original',
    'province': 'provincia',
    'municipality': 'municipi',
    'district': 'districte',
    'neighborhood': 'barri',
    'address': 'adreça',
    'postcode': 'codi_postal',
    'width': 'ample',
    'height': 'alt',
    'camera_model': 'model_camara',
    'flickr_id': 'id_flickr',
    'flickr_username': 'usuari_flickr',
    'title': 'titol',
    'description': 'descripcio',
    'album': 'album',
    'author': 'autor',
    'copyright': 'drets_autor',
    'restriction': 'llicencia',
}

PRIVATE_API_SCHEMA_URL = 'private_api/docs/'
PUBLIC_API_SCHEMA_URL = 'public_api/docs/'

CACHE_USER_PROFILE_PREFIX_KEY = 'user'
CACHE_SCHEMA_PREFIX_KEY = 'schema'
CACHE_TAXONOMY_PREFIX_KEY = 'taxonomy'

NOT_ASSIGNED_AUTOCOMPLETE_CHOICE_TEXT = _('Unassigned')
NOT_ASSIGNED_AUTOCOMPLETE_CHOICE_ID = -1
NOT_ASSIGNED_CHOICES = [
    (NOT_ASSIGNED_AUTOCOMPLETE_CHOICE_ID, NOT_ASSIGNED_AUTOCOMPLETE_CHOICE_TEXT)
]
