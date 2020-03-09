# -*- coding: utf-8 -*-
import re

from constance import config
from django import forms
from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse_lazy
from django.utils.translation import ugettext as _
from geoposition.forms import GeopositionField

from .fields import Select2Field, Select2MultipleField, Select2TagField
from .mixins import UnpackingMixin, FieldsetFormMixin, TranslatableFormMixin, UnassignedMixin
from .constants import LOG_ACTIONS, PHOTO_STATUS_CHOICES, BLANK_CHOICES


EXIF_DATE_FORMAT = '%d/%m/%Y'

IMAGE_FORMATS = ('gif', 'jpeg', 'jpg', 'png', 'tif', 'tiff', 'psd')

# from https://support.google.com/youtube/troubleshooter/2888402?hl=en
VIDEO_FORMATS = ('mov', 'mpeg4', 'mp4', 'avi', 'wmv', 'mpegps', 'flv', '3gpp', 'webm')

# from https://help.soundcloud.com/hc/en-us/articles/115003452847-Uploading-requirements
AUDIO_FORMATS = ('aiff', 'wav', 'flac', 'alac', 'ogg', 'mp2', 'mp3', 'aac', 'amr', 'wma')

FORMATS = IMAGE_FORMATS + VIDEO_FORMATS + AUDIO_FORMATS


class FilterBase(forms.Form):
    """
    This class extends to forms.Form, so has bootstrap style and moreover sets all fields as not required
    """
    allow_blank = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.required = False

    def clean(self):
        cleaned_data = super().clean()
        if not self.allow_blank:
            return {key: value for key, value in cleaned_data.items() if value}
        return cleaned_data


class PhotoEditBase(forms.Form):
    """
    Base photo form to set fields as not required
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not getattr(settings, 'PHOTO_AUTHOR_REQUIRED', True):
            self.fields['author'].required = False
        if not getattr(settings, 'PHOTO_COPYRIGHT_REQUIRED', True):
            self.fields['copyright'].required = False
        if not getattr(settings, 'PHOTO_DATE_REQUIRED', True):
            self.fields['exif_date'].required = False


class AlbumForm(TranslatableFormMixin, forms.Form):
    """
    Form to create a new album
    """

    translatable_fields = (
        ('title', {'type': TranslatableFormMixin.CHAR, 'label': _('Title'), 'required': True, 'max_length': 128}),
        ('description', {'type': TranslatableFormMixin.TEXT, 'label': _('Description'), 'required': False}),
    )

    slug = forms.SlugField(label=_('Slug'))
    owners = Select2MultipleField(data_view='user_search', label=_('Assignee'))

    def __init__(self, owners=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if owners:
            self.fields['owners'].widget.choices = owners


class AlbumPhotoCreateForm(TranslatableFormMixin, PhotoEditBase):
    """
    Form to upload photos to a preselected album
    """
    translatable_fields = (
        ('title', {'type': TranslatableFormMixin.CHAR, 'label': _('Title'), 'required': True, 'max_length': 128}),
        ('keywords', {
            'type': TranslatableFormMixin.SELECT_MULTILANG_TAG,
            'label': _('Keywords'),
            'required': getattr(settings, 'PHOTO_KEYWORDS_REQUIRED', False),
            'data_view': 'keyword_search'}),
        ('description', {'type': TranslatableFormMixin.TEXT, 'label': _('Description'),
                         'required': False}),
    )

    upload_id = forms.CharField(widget=forms.widgets.HiddenInput())
    author = Select2Field(data_view='author_search', label=_('Author'))
    copyright = Select2Field(data_view='copyright_search', label=_('Copyright'))
    exif_date = forms.DateField(label=_('Capture date'), input_formats=[EXIF_DATE_FORMAT])


class PhotoCreateForm(AlbumPhotoCreateForm):
    """
    Form to upload photos with an album field to select
    """
    album = Select2Field(data_view='album_search', label=_('Album'))


class PhotoEditForm(UnpackingMixin, FieldsetFormMixin, TranslatableFormMixin, PhotoEditBase):
    """
    Form to edit a photo
    """

    unpack_field_translatable_names = ('keywords', )
    unpack_field_names = ('album', 'categories', 'galleries', 'names', 'author', 'copyright',
                          'internal_usage_restriction', 'external_usage_restriction', )

    metadata_fields = ['keywords', 'categories', 'names', ]

    if getattr(settings, 'PHOTO_TYPES_ENABLED', False):
        unpack_field_names += ('photo_type', )
        metadata_fields += ['photo_type', ]
        photo_type = Select2Field(data_view='type_search', label=getattr(settings, 'PHOTO_TYPES_NAME', _('Type')),
                                  required=False)

    fieldsets = (
        ('general', {'fields': ['title', 'description', 'album', 'galleries', 'status', 'exif_date', 'image',
                                'upload_id'],
                     'title': _('General information')}),
        ('metadata', {'fields': metadata_fields, 'title': _('Metadata')}),
        ('copyright', {'fields': ['author', 'internal_usage_restriction', 'copyright', 'external_usage_restriction'],
                       'title': _('Copyright')}),
        ('location', {'fields': ['position', 'address', 'postcode', 'neighborhood', 'district'],
                      'title': _('Location')})
    )

    translatable_fields = (
        ('title', {'type': TranslatableFormMixin.CHAR, 'label': _('Title'), 'required': True, 'max_length': 128}),
        ('keywords', {
            'type': TranslatableFormMixin.SELECT_MULTILANG_TAG,
            'label': _('Keywords'),
            'required': getattr(settings, 'PHOTO_KEYWORDS_REQUIRED', False),
            'data_view': 'keyword_search'}),
        ('description', {'type': TranslatableFormMixin.TEXT, 'label': _('Description'), 'required': False}),
    )

    # general
    album = Select2Field(data_view='album_search', label=_('Album'))
    galleries = Select2MultipleField(data_view='gallery_search', label=_('Galleries'), required=False)
    status = forms.ChoiceField(label=_('Status'), choices=PHOTO_STATUS_CHOICES, required=False)
    exif_date = forms.DateField(label=_('Capture date'), input_formats=[EXIF_DATE_FORMAT])
    image = forms.FileField(label=_('Change File'), required=False)
    upload_id = forms.CharField(widget=forms.widgets.HiddenInput(), required=False)
    # metadata
    categories = Select2MultipleField(data_view='category_search', label=_('Categories'), required=False)
    names = Select2TagField(data_view='name_search', label=_('Names'), required=False)
    # copyright
    author = Select2Field(data_view='author_search', label=_('Author'))
    copyright = Select2Field(data_view='copyright_search', label=_('Copyright'))
    internal_usage_restriction = Select2Field(data_view='restriction_search', label=_('Internal restriction'),
                                              required=False)
    external_usage_restriction = Select2Field(data_view='restriction_search', label=_('External restriction'),
                                              required=False)
    # location
    position = GeopositionField(label=_('Position'), required=False)
    address = forms.CharField(label=_('Address'), max_length=200, required=False)
    district = forms.CharField(label=_('District'), max_length=128, required=False)
    neighborhood = forms.CharField(label=_('Neighborhood'), max_length=128, required=False)
    postcode = forms.CharField(label=_('Postcode'), max_length=128, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.initial.get('image_flickr', ''):
            self.fields['image'].widget = forms.widgets.HiddenInput()

        # add attributes to update image
        self.fields['image'].widget.attrs.update({
            'data-chunk-url': reverse_lazy('api_chunked_upload'),
            'data-chunk-complete-url': reverse_lazy('api_chunked_upload_complete'),
            'data-chunk-size': config.PHOTO_UPLOAD_CHUNK_SIZE,
            'data-error-msg': _('An error has occurred. Please, try again.'),
            'data-max-file-size': config.MAX_FILE_SIZE,
            'data-max-size-message': "{} {} {}".format(
                _('Sorry, the maximum file size allowed is'),
                config.MAX_FILE_SIZE,
                _('MB')),
            'data-max-photo-file-size': config.MAX_PHOTO_FILE_SIZE,
            'data-max-photo-file-size-message': "{} {} {}".format(
                _('Sorry, the maximum image file size allowed is'),
                config.MAX_PHOTO_FILE_SIZE,
                _('MB')),
            'data-file-type-message': "{}: {}.".format(
                _('Sorry, only the following formats are allowed'),
                ', '.join(FORMATS)),
            'data-loading-gif': staticfiles_storage.url('bima_back/img/loader.gif'),
        })

        # add youtube and vimeo codes for videos
        if kwargs.get('initial', {}).get('file_type') == 'video':
            self.fieldsets[0].fields.extend(('youtube_code', 'vimeo_code'))
            self.fields['youtube_code'] = forms.CharField(label=_('Youtube code'), required=False)
            self.fields['vimeo_code'] = forms.CharField(label=_('Vimeo code'), required=False)


class PhotoEditMultipleForm(PhotoEditForm):
    """
    Form to edit multiple photos. In this case, no fields are required.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        not_required_fields = ['album', 'author', 'copyright', 'exif_date']
        for field in not_required_fields:
            self.fields[field].required = False

        for field in self.fields:
            if field.startswith('title'):
                self.fields[field].required = False

        self.fields['image'].widget = forms.widgets.HiddenInput()
        self.fields['status'].widget.choices = [('', '----')] + PHOTO_STATUS_CHOICES


class YoutubeChannelForm(forms.Form):
    youtube_channel = forms.ChoiceField(label='', widget=forms.RadioSelect)

    def __init__(self, youtube_channels, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = [(ch['id'], self._channel_label(ch)) for ch in youtube_channels]
        self.fields['youtube_channel'].widget.choices = choices
        self.fields['youtube_channel'].initial = choices[0][0]

    @staticmethod
    def _channel_label(ch):
        return '{} - {}'.format(ch['name'], ch['account']['username'])


class VimeoAccountForm(forms.Form):
    vimeo_account = forms.ChoiceField(label='', widget=forms.RadioSelect)

    def __init__(self, vimeo_accounts, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = [(va['id'], self._account_label(va)) for va in vimeo_accounts]
        self.fields['vimeo_account'].widget.choices = choices
        self.fields['vimeo_account'].initial = choices[0][0]

    @staticmethod
    def _account_label(account):
        if not account['username']:
            return account['name']
        return '{} - {}'.format(account['name'], account['username'])


class GalleryForm(TranslatableFormMixin, forms.Form):
    """
    Form to create a new gallery
    """

    translatable_fields = (
        ('title', {'type': TranslatableFormMixin.CHAR, 'label': _('Title'), 'required': True, 'max_length': 128}),
        ('description', {'type': TranslatableFormMixin.TEXT, 'label': _('Description'), 'required': False}),
    )

    slug = forms.SlugField(label=_('Slug'))
    owners = Select2MultipleField(data_view='user_search', label=_('Assignees'))
    status = forms.ChoiceField(label=_('Status'), choices=PHOTO_STATUS_CHOICES, required=False)

    def __init__(self, owners=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if owners:
            self.fields['owners'].widget.choices = owners


class CategoryForm(TranslatableFormMixin, forms.Form):
    """
    Form to create a new category
    """

    translatable_fields = (
        ('name', {'type': TranslatableFormMixin.CHAR, 'label': _('Name'), 'required': True, 'max_length': 128}),
    )

    parent = Select2Field(data_view='category_search', label=_('Parent'), required=False)
    slug = forms.SlugField(label=_('Slug'))

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if parent:
            self.fields['parent'].widget.choices = parent


class AlbumFlickrForm(forms.Form):
    """
    Form to import a flickr photo to a preselected album
    """
    author = Select2Field(data_view='author_search', label=_('Author'))
    copyright = Select2Field(data_view='copyright_search', label=_('Copyright'))
    url = forms.CharField(label=_('Flickr URL'),
                          help_text=_('For example: https://www.flickr.com/photos/name/123456789/in/other'))

    def clean_url(self):
        """
        Confirms that the flickr url is valid, if it has the numeric id.
        """
        data = self.cleaned_data['url']
        url_id = re.search('/\d+/', data)
        if not url_id or 'flickr.com' not in data:
            raise forms.ValidationError("Invalid flickr url")
        return data


class FlickrForm(AlbumFlickrForm):
    """
    Form to import a flickr photo with an album field to select it.
    """
    id = Select2Field(data_view='album_search', label=_('Album'))


class PasswordResetForm(forms.Form):
    email = forms.EmailField(label=_('E-mail'))


class PasswordChangeForm(forms.Form):
    new_password1 = forms.CharField(label=_('New password'), max_length=128, widget=forms.PasswordInput())
    new_password2 = forms.CharField(label=_('Repeat new password'), max_length=128, widget=forms.PasswordInput())

    def __init__(self, *args, **kwargs):
        super(PasswordChangeForm, self).__init__(*args, **kwargs)
        self.fields['new_password1'].widget.attrs['onkeyup'] = "checkPassChange(); return false;"
        self.fields['new_password2'].widget.attrs['onkeyup'] = "checkPassChange(); return false;"

    def clean(self):
        cleaned_data = super(PasswordChangeForm, self).clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')

        if new_password1 != new_password2:
            raise forms.ValidationError(
                _("Passwords don't match")
            )


class UserForm(forms.Form):
    """
    Form to edit user data
    """

    first_name = forms.CharField(label=_('First name'), max_length=30, required=False)
    last_name = forms.CharField(label=_('Last name'), max_length=30, required=False)
    groups = forms.CharField(label=_('Group'), widget=forms.widgets.RadioSelect())

    def __init__(self, groups=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if groups:
            self.fields['groups'].widget.choices = groups


# Filters

class AdvancedSemanticSearchForm(UnassignedMixin, UnpackingMixin, FilterBase):
    """
    Searcher form try to look for photos matching for the requested text.
    Searcher form try to look for photos matching for each one of next fields.
    - title
    - description
    """
    unpack_field_names = ('album', 'categories', 'gallery', )
    unassigned_field_names = ('categories', 'gallery', )
    if getattr(settings, 'PHOTO_TYPES_ENABLED', False):
        unpack_field_names += ('photo_type', )
        unassigned_field_names += ('photo_type', )

    # semantic search
    q = forms.CharField(help_text=_('Set text or part of text you want to search into the assets'), label=_('Text'))
    # advanced accurate search
    title = forms.CharField(label=_('Title'))
    description = forms.CharField(label=_('Description'))
    album = Select2MultipleField(data_view='album_search', label=_('Albums'))
    categories = Select2MultipleField(data_view='category_search', label=_('Categories'))
    gallery = Select2MultipleField(data_view='gallery_search', label=_('Galleries'))
    status = forms.ChoiceField(choices=BLANK_CHOICES + PHOTO_STATUS_CHOICES, label=_('Status'))
    if getattr(settings, 'PHOTO_TYPES_ENABLED', False):
        photo_type = Select2MultipleField(data_view='type_search', label=_('Types'))

    def clean(self):
        """
        Clean only one of advanced search or semantic search.
        """
        data = super().clean()
        q = data.pop('q', None)
        if q:
            return {'q': q}
        return data

    def is_advanced_search(self):
        """
        :return: True if the user has searched using advanced fields.
        """
        data = self.cleaned_data
        return self.is_bound and any([
            data.get('title'),
            data.get('description'),
            data.get('album'),
            data.get('categories'),
            data.get('gallery'),
            data.get('status'),
            data.get('photo_type', ''),
        ])


class LogFilterForm(FilterBase):
    """
    Form to filter log by
    - action
    - added_at
    """
    blank_option = [('', '----')]
    ACTION_CHOICES = blank_option + LOG_ACTIONS

    action = forms.ChoiceField(label=_('Action'), choices=ACTION_CHOICES)
    user = Select2Field(data_view='user_search', label=_('User'))
    added_from = forms.DateField(label=_('From'), input_formats=['%Y-%m-%d'])
    added_to = forms.DateField(label=_('To'), input_formats=['%Y-%m-%d'])

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['user'].widget.choices = user


class CategoryFilterForm(FilterBase):
    """
    Form to filter categories by name
    """
    name = forms.CharField(label=_('Name'), max_length=128)


class GalleryFilterForm(FilterBase):
    """
    Form to filter gallery by title and status (private/published)
    """
    ALL = ''
    PRIVATE = 0
    PUBLISHED = 1

    STATUS_CHOICES = [
        (ALL, _('All')),
        (PRIVATE, _('Private')),
        (PUBLISHED, _('Published')),
    ]

    title = forms.CharField(label=_('Title'), max_length=128)
    status = forms.ChoiceField(label=_('Status'), choices=STATUS_CHOICES)


class AlbumFilterForm(FilterBase):
    """
    Form to filter album by title
    """
    title = forms.CharField(label=_('Title'), max_length=128)
