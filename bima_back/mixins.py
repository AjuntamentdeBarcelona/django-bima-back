# -*- coding: utf-8 -*-
from braces.views import FormMessagesMixin

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import redirect
from django.utils.module_loading import import_string
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import ContextMixin
from django.views.generic.edit import FormMixin

from .fields import TextField, Select2MultilangTagField
from .service import ServiceClientException
from .utils import get_language_codes


class PaginatorMixin(object):
    """
    Mixin to paginate service client requests
    """
    def get_current_page(self):
        """
        Returns page get parameter or 1
        """
        return self.request.GET.get('page', '1')

    def paginate(self, count, per_page):
        return Paginator(range(count), per_page).page(self.get_current_page())


class FilterFormMixin(FormMixin):
    form_context = None
    http_method_names = ('get', )

    def get_form_kwargs(self):
        """
        Returns the keyword arguments for instantiating the form.
        """
        self.form_context = self.get_form_context()
        kwargs = {'initial': self.get_initial(), 'prefix': self.get_prefix()}
        if self.request.method.lower() in self.http_method_names:
            kwargs.update({'data': self.request.GET})
        return kwargs

    def get_form_context(self):
        return {}


class Fieldset(object):
    """
    An iterable Fieldset with a legend and a set of BoundFields.
    """

    def __init__(self, form, name, fields, icon='', title='', css_class=''):
        self.form = form
        self.fields = fields
        self.name = mark_safe(name or '')
        self.icon = mark_safe(icon or '')
        self.title = mark_safe(title or '')
        self.css_class = mark_safe(css_class or '')
        pass

    def __iter__(self):
        for name in self.fields:
            yield self.form[name]

    def __getitem__(self, name):
        try:
            field = self.form.fields[name]
        except KeyError:
            raise KeyError("Key '{}' not found in '{}'.".format(name, self.form.__class__))
        if name not in self.form._bound_fields_cache:
            self.form._bound_fields_cache[name] = field.get_bound_field(self, name)
        return self.form.form_bound_fields_cache[name]


class FieldsetFormMixin(object):
    """
    Mixin to set fieldsets of a form
    """

    fieldsets = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._get_fieldsets()

    def _get_fieldsets(self):
        if not self.fieldsets:
            self.fieldsets = (
                ('main', {'fields': self.fields.keys()}, )
            )

        _fieldsets, _processed = [], []
        for name, options in self.fieldsets:
            if 'fields' not in options:
                raise ValueError("Fieldset definition must include 'fields' option.")

            fields, translatable_field_names = [], getattr(self, 'translatable_field_names', [])
            for field_name in options['fields']:
                if not translatable_field_names and hasattr(self, 'translatable_fields'):
                    translatable_field_names.extend([field for field, *options in self.translatable_fields])

                if field_name in translatable_field_names:
                    fields.extend(["{}_{}".format(field_name, code) for code in get_language_codes()])
                else:
                    fields.append(field_name)

            _processed.extend(fields)
            _fieldsets.append(
                Fieldset(self, name, fields, options.get('icon', ''), options.get('title', ''),
                         options.get('css_class', ''))
            )

        # add default fieldset (extra) with all declared fields which has not fieldset defined
        fields = set(self.fields.keys()) - set(_processed)
        if fields:
            _fieldsets.append(Fieldset(self, 'extra', fields, title=_('Extra information')))
        self.fieldsets = _fieldsets


class TranslatableFormMixin(object):
    """
    Mixin to generate form fields in the available languages,
    setting options as label, required, max_length, fieldtype...
    """

    CHAR = 'char'
    TEXT = 'text'
    SELECT = 'select'
    SELECT_MULTIPLE = 'select-multiple'
    SELECT_TAG = 'select-tag'
    SELECT_MULTILANG_TAG = 'select-multilang-tag'

    FIELD_TYPES = {
        CHAR: forms.CharField,
        TEXT: TextField,
        SELECT_MULTILANG_TAG: Select2MultilangTagField,
    }

    AUTOCOMPLETE_FIELDS = (SELECT, SELECT_MULTIPLE, SELECT_TAG, SELECT_MULTILANG_TAG, )

    translatable_fields = ()
    translatable_field_names = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_translatable_fields()

    def get_translatable_fields(self):
        if not self.translatable_fields:
            raise ValidationError('Is required define translatable fields for {}'.format(self.__class__))
        return self.translatable_fields

    def add_translatable_fields(self):
        _translatable_field_names = []
        for field_name, options in self.get_translatable_fields():
            _translatable_field_names.append(field_name)
            self.fields.update(self.clean_translatable_fields(field_name, **options))
        self.translatable_field_names = tuple(_translatable_field_names)

    def clean_translatable_fields(self, field_name, **kwargs):
        # validation required field definition
        if not (field_name and 'type' in kwargs):
            raise ValidationError('Invalid definition of translatable field in {}'.format(self.__class__))

        # validation for a type of field
        field_type, field_data_view = kwargs.get('type'), kwargs.get('data_view')
        if field_type in self.AUTOCOMPLETE_FIELDS and not field_data_view:
            raise ValidationError('An url name is required for autocomplete fields in {}'.format(self.__class__))

        field_required = kwargs.get('required', False) or False
        field_kwargs = {'label': kwargs.get('label') or _(field_name.capitalize())}
        if field_type in self.AUTOCOMPLETE_FIELDS:
            field_kwargs.update({'data_view': field_data_view})

        translatable_fields = {}
        for code in get_language_codes():
            field = self.FIELD_TYPES.get(field_type, forms.CharField)
            field_kwargs.update({
                'required': field_required and code == settings.LANGUAGE_CODE,
                'max_length': kwargs.get('max_length'),
                'min_length': kwargs.get('min_length'),
            })
            # special case that need extra argument 'language'
            if field_type == self.SELECT_MULTILANG_TAG:
                field_kwargs.update({'language': code})

            translatable_field = field(**field_kwargs)
            # expand widget class with 'i18nfield' tag
            widget_class = translatable_field.widget.attrs.get('class') or '' + ' i18nfield'
            translatable_field.widget.attrs['class'] = widget_class
            # add lang for browser spellcheck
            translatable_field.widget.attrs['spellcheck'] = "true"
            translatable_field.widget.attrs['lang'] = code

            # update translatable fields
            translatable_fields["{}_{}".format(field_name, code)] = translatable_field

        return translatable_fields


class UnpackingMixin(object):
    """
    Mixin to set initial form choices
    """

    unpack_field_names = ()
    unpack_field_translatable_names = ()

    def __init__(self, *args, **kwargs):
        """
        This method receive the options (choices) from client request to preselect initial fields forms
        """

        initial_field_choices = []
        for field_name in self.unpack_field_names:
            initial_field_choices.append((field_name, kwargs.pop(field_name, None)))

        for field_name in self.unpack_field_translatable_names:
            for code in get_language_codes():
                name = "{}_{}".format(field_name, code)
                initial_field_choices.append((name, kwargs.pop(name, None)))

        super().__init__(*args, **kwargs)

        # set choices
        for field, choices in initial_field_choices:
            if choices:
                self.fields[field].widget.choices = choices


class UnassignedMixin(object):
    """
    Mixin to append Unassigned option
    """
    unassigned_field_names = ()
    unassigned_field_class = 'show-unassigned-choice'

    def __init__(self, *args, **kwargs):
        """
        This method append unassigned choice
        """
        super().__init__(*args, **kwargs)
        for field_name in self.unassigned_field_names:
            self.fields[field_name].widget.attrs.update({'class': self.unassigned_field_class})


class MessageMixin(FormMessagesMixin):
    """
    Extended mixin from 'From message mixin' which set static message to display on the front page
    """
    form_valid_message = _("Your transaction completed successfully.")
    form_invalid_message = _("Ooops! Something went wrong.")

    def success_message(self, success_message=''):
        return success_message or super().get_form_valid_message()

    def error_message(self, error_message=''):
        return error_message or super().get_form_invalid_message()


class ServiceClientMixin(MessageMixin, ContextMixin):
    """
    Mixin to get action to Web service
    """
    restore_action_name = ''
    action_name = ''

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except ServiceClientException as exc:
            if exc.code_error in (401, 403):
                logout(request)
                self.error_message(_("You don't have permissions to do this action! Log in."))
                return redirect('home')
            elif exc.code_error == 404:
                raise Http404
            elif exc.code_error == 400:
                if hasattr(exc.args[1], 'error'):
                    msg = exc.args[1].error.get_messages()
                    messages.add_message(request, messages.ERROR, msg[0] if msg else _("Ooops! Something went wrong."))
                    return redirect(request.path)
                else:
                    raise Http404
            raise ServiceClientException(500, "Generic error")

    def get_client(self):
        """
        :return: Client instance
        """
        client_class_name = 'bima_back.service.DAMWebService'
        if hasattr(settings, 'WEB_SERVICE_CLIENT_CLASS') and settings.WEB_SERVICE_CLIENT_CLASS:
            client_class_name = settings.WEB_SERVICE_CLIENT_CLASS

        client_class = import_string(client_class_name)

        return client_class(self.request)

    def get_action_name(self):
        """
        Used when an single action has to execute in the view
        :return: action to execute through web service to do an action
        """
        if not self.action_name:
            raise NotImplementedError
        return self.action_name

    def get_client_action(self, action=None, safe=False):
        """
        Get the action from the service if exists
        :param safe: indicate if is required raise an error
        :param action: name of the action to execute
        :return: a function or None if safe is default set, otherwise raise error 500
        """
        action = getattr(self.get_client(), action or self.get_action_name(), None)
        if not safe and action is None:
            raise ServiceClientException(500, 'Error getting action client')
        return action

    def get_restore_action_name(self):
        """
        Used when is needed get information previously execute a single action in the view
        :return: action to execute through web service to get data
        """
        if not self.restore_action_name:
            raise NotImplementedError
        return self.restore_action_name

    def get_client_restore_action(self, action=None, safe=False):
        """
        Get the action from the service if exists
        :param safe: indicate if is required raise an error
        :param action: name of the action to execute
        :return: idem 'get_client_action' to restore action name
        """
        action = getattr(self.get_client(), action or self.get_restore_action_name(), None)
        if not safe and action is None:
            raise ServiceClientException(500, 'Error getting restore action client')
        return action


class LoggedServiceMixin(LoginRequiredMixin, ServiceClientMixin):
    """
    Mixin to unify most frequency used mixins on views: Login, ServiceClient
    """


class LoggedServicePaginatorMixin(LoggedServiceMixin, PaginatorMixin):
    """
    Mixin to unify most frequency used mixins on views: Login, ServiceClient, LoggedServiceMixin
    """


# Proxy models

class ModelMixin(object):

    @property
    def user(self):
        return getattr(self.request, 'user', None)

    @property
    def permissions(self):
        return self.user.permissions


class AlbumMixin(ModelMixin):

    @property
    def album_owners(self):
        return self.instance['extra_info']['owners']


class GalleryMixin(ModelMixin):

    @property
    def gallery_owners(self):
        return self.instance['extra_info']['owners']


class CategoryMixin(ModelMixin):

    @property
    def category_parent_id(self):
        return self.instance['extra_info']['parent']['id']

    @property
    def category_parent_title(self):
        return self.instance['extra_info']['parent']['title']


class PhotoMixin(ModelMixin):

    @property
    def photo_galleries(self):
        return self.instance['extra_info']['photo_galleries']

    @property
    def photo_names(self):
        return self.instance['names']

    @property
    def photo_keywords(self):
        return self.instance['keywords']

    @property
    def photo_album_selected(self):
        return self.instance['album'], self.instance['extra_info']['album']['title']

    @property
    def photo_author_selected(self):
        extra_info = self.instance['extra_info']
        if 'author_display' in extra_info and extra_info['author_display']:
            return self.instance['author'], extra_info['author_display']
        return None, ''

    @property
    def photo_copyright_selected(self):
        extra_info = self.instance['extra_info']
        if 'copyright_display' in extra_info and extra_info['copyright_display']:
            return self.instance['copyright'], extra_info['copyright_display']
        return None, ''

    @property
    def photo_internal_restriction_selected(self):
        extra_info = self.instance['extra_info']
        if 'internal_restriction_display' in extra_info and extra_info['internal_restriction_display']:
            return self.instance['internal_restriction'], extra_info['internal_restriction_display']
        return None, ''

    @property
    def photo_external_restriction_selected(self):
        extra_info = self.instance['extra_info']
        if 'external_usage_restriction' in extra_info and extra_info['external_usage_restriction']:
            return self.instance['external_usage_restriction'], extra_info['external_usage_restriction']
        return None, ''

    @property
    def photo_type_selected(self):
        if 'photo_type' in self.instance['extra_info'] and self.instance['extra_info']['photo_type']:
            return self.instance['extra_info']['photo_type']['id'], self.instance['extra_info']['photo_type']['name']
        return None, None

    @property
    def photo_categories(self):
        return self.instance['extra_info']['categories']

    def photo_gallery_permission(self, action):
        return self.permissions['gallery'][action]
