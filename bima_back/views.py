# -*- coding: utf-8 -*-
from datetime import datetime
import re

from braces.views import JSONResponseMixin, AjaxResponseMixin
from chunked_upload.views import ChunkedUploadView, ChunkedUploadCompleteView
from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.urls import reverse, reverse_lazy
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.utils.translation import ugettext as _
from django.views.generic.base import View, TemplateView, RedirectView
from django.views.generic.edit import FormView

from .constants import CACHE_USER_PROFILE_PREFIX_KEY, NOT_ASSIGNED_AUTOCOMPLETE_CHOICE_ID, \
    NOT_ASSIGNED_AUTOCOMPLETE_CHOICE_TEXT
from .exports import LogReport
from .forms import AlbumForm, PhotoCreateForm, UserForm, GalleryForm, PhotoEditForm, \
    CategoryForm, FlickrForm, LogFilterForm, PhotoEditMultipleForm, AdvancedSemanticSearchForm, \
    AlbumPhotoCreateForm, AlbumFlickrForm, CategoryFilterForm, YoutubeChannelForm, VimeoAccountForm, \
    GalleryFilterForm, AlbumFilterForm
from .mixins import ServiceClientMixin, LoggedServicePaginatorMixin, LoggedServiceMixin, FilterFormMixin, \
    PaginatorMixin, PhotoMixin, AlbumMixin, GalleryMixin, CategoryMixin
from .models import MyChunkedUpload
from .tasks import upload_photo
from .utils import get_language_codes, get_class_name, get_choices_ids, get_choices, get_tag_choices, format_date, \
    cache_set, prepare_params, prepare_keywords, change_form_tag_languages
from .service import UploadStatus


# index

class HomeView(LoggedServicePaginatorMixin, FormView):
    template_name = 'bima_back/home.html'
    form_class = AdvancedSemanticSearchForm
    action_name = 'photos_list'


# list views

class BaseListView(LoggedServicePaginatorMixin, FilterFormMixin, TemplateView):
    lookup_object = None
    active_section = ''

    def get_lookup_object(self):
        if not self.lookup_object:
            raise NotImplementedError
        return self.lookup_object

    def service_list_function(self, **kwargs):
        return self.get_client_action()(**kwargs)

    def add_params(self, params):
        return params

    @staticmethod
    def edit_filter_params(cleaned_data):
        return cleaned_data

    def get_context_data(self, **kwargs):
        # get filter form params to search through service client
        form, params = None, {'page': self.get_current_page()}
        params = self.add_params(params)
        if self.get_form_class():
            form = self.get_form()
            if form.is_valid():
                cleaned_data = form.cleaned_data
                self.edit_filter_params(cleaned_data)
                params.update(**cleaned_data)
        response = self.service_list_function(**params)
        # get context and update with results from service
        context = super().get_context_data(form=form, **kwargs)
        context.update({
            'page': self.paginate(response['count'], response['per_page']),
            self.get_lookup_object(): response['results'],
            'active_section': self.active_section,
        })
        return context


class AlbumListView(BaseListView):
    template_name = 'bima_back/albums/album.html'
    lookup_object = 'albums'
    action_name = 'get_albums_list'
    form_class = AlbumFilterForm
    active_section = 'album'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['show_public_album'] = self.show_public_album(self.request.GET)
        return ctx

    def show_public_album(self, get_params):
        """
        Show public album when:
        - We are in first page (no GET parameters or `page` parameter is 1).
        And:
        - No search has been done (no parameters different than page in GET or all parameters empty except page)
        """

        # Get parameters values other than page:
        parameters_values = [get_params.get(parameter) for parameter in get_params if parameter != 'page']

        is_first_page = get_params.get('page') == '1' or not get_params
        no_search = not parameters_values or not any(parameters_values)
        return is_first_page and no_search


class PhotoListView(PhotoMixin, BaseListView):
    template_name = 'bima_back/photos/photo.html'
    lookup_object = 'photos'
    action_name = 'get_photos_list'
    form_class = AdvancedSemanticSearchForm
    active_section = 'photo'

    def service_list_function(self, **kwargs):
        """
        This overwrites to allow expand form criteria and custom api search
        Only if it has 'q' filter and 'page' in kwargs, will do the semantic search
        """
        q_filter = kwargs.pop('q', None)
        if q_filter and len(kwargs) == 1:
            self.action_name = 'search_photos_list'
            q_filter = change_form_tag_languages(q_filter)
            kwargs.update({'q': q_filter})
        return self.get_client_action(self.action_name)(**kwargs)

    def get_instance_list(self, action, params):
        """
        Do request through API to get list of items filtered by id.
        :param action: string of method definition name of client api service.
        :param params: value or list of values to filter
        """
        return self.get_client_action(action)(**{'id': params})['results']

    def get_form_context(self):
        """
        Iterate over 'request_for_fields' list defined as multiple elements of <<field, service_action>>, to build
        a dictionary for all fields which have values. It gets a single value or list according the
        'multi_valuated_fields' field list.
        """
        context = {}
        request_for_fields = (('album', 'get_albums_list'), ('categories', 'get_categories_simple_list'),
                              ('gallery', 'get_galleries_list'))
        if getattr(settings, 'PHOTO_TYPES_ENABLED', False):
            request_for_fields += (('photo_type', 'get_photo_type_list'), )

        for field, action in request_for_fields:
            get_values = getattr(self.request.GET, 'getlist', [])
            value = get_values(field)
            if value:
                context.update({field: self.get_instance_list(action, value)})
        return context

    def get_form_kwargs(self):
        """
        Prepare kwargs with field choices from form context.
        """
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'album': get_choices(self.form_context.get('album'), text='title'),
            'categories': get_choices(self.form_context.get('categories'), text='name', has_unassigned=True),
            'gallery': get_choices(self.form_context.get('gallery'), text='title', has_unassigned=True),
        })
        if getattr(settings, 'PHOTO_TYPES_ENABLED', False):
            kwargs.update({
                'photo_type': get_choices(self.form_context.get('photo_type'), text='name', has_unassigned=True),
            })
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['not_assigned_choice_id'] = NOT_ASSIGNED_AUTOCOMPLETE_CHOICE_ID
        ctx['not_assigned_choice_text'] = NOT_ASSIGNED_AUTOCOMPLETE_CHOICE_TEXT
        return ctx


class GalleryListView(BaseListView):
    template_name = 'bima_back/galleries/gallery.html'
    lookup_object = 'galleries'
    action_name = 'get_galleries_list'
    form_class = GalleryFilterForm
    active_section = 'gallery'


class CategoryListView(BaseListView):
    template_name = 'bima_back/categories/category.html'
    lookup_object = 'categories'
    action_name = 'get_categories_level_list'
    form_class = CategoryFilterForm
    active_section = 'category'

    def add_params(self, params):
        """
        This adds the parameter root to the query in order to get the list
        of root categories with its children.
        """
        params.update({'root': "True"})
        return params

    @staticmethod
    def edit_filter_params(cleaned_data):
        """
        This updates cleaned data because when we search for a category
        by name, we want to obtain all results, no matter the level
        of the category
        """
        if cleaned_data:
            cleaned_data.update({'root': ''})
        return cleaned_data

    def get_context_data(self, **kwargs):
        """
        In case of category search, update context with the results
        """
        context = super().get_context_data(**kwargs)
        if self.get_form_class():
            form = self.get_form()
            if form.is_valid():
                if form.cleaned_data:
                    results = context[self.lookup_object]
                    final_result = self.process_result(results)
                    context.update({self.lookup_object: final_result})
        return context

    @staticmethod
    def process_result(results):
        """
        This processes category search results to return the level 0 category
        with its children.
        The search by default returns the wanted category with its parents.
        """
        final_result = []
        for result in results:
            category = {'extra_info': {'children': result['extra_info']['children']}}
            if result['extra_info']['parent']:
                name = '{} | ({})'.format(result['name'], result['extra_info']['parent']['title'])
            else:
                name = '{}'.format(result['name'])
            category.update({
                'id': result['id'],
                'name': name,
                'children': [{}],
            })
            final_result.append(category)
        return final_result


class CategoryChildrenAjaxListView(JSONResponseMixin, AjaxResponseMixin, LoggedServiceMixin, View):
    def get_ajax(self, request, *args, **kwargs):
        action = self.get_client_action('get_categories_level_list')
        params = {'parent': request.GET.get('parent')}
        response = action(**params)
        return self.render_json_response(response)


class LogListView(BaseListView):
    template_name = 'bima_back/logs/log.html'
    lookup_object = 'logs'
    action_name = 'get_log_list'
    form_class = LogFilterForm

    def get_context_data(self, **kwargs):
        """
        If csv export requested, adds the resulting logs to the context
        """
        if 'csv' in self.request.GET.get('export', ''):
            params = self.request.GET.dict()
            params.pop('export', None)  # param not supported by service
            response = self.service_list_function(**params)
            return {'export-report': response['results']}
        return super().get_context_data(**kwargs)

    def render_to_response(self, context, **response_kwargs):
        """
        Creates a CSV response if requested, otherwise returns the default
        template response.
        """
        # Sniff if we need to return a CSV export
        if 'export-report' in context:
            report = LogReport(data=context.get('export-report'), user=self.request.user)
            response = HttpResponse(report.csv, content_type=report.content_type)
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(report.file_name)
            return response
        return super(LogListView, self).render_to_response(context, **response_kwargs)

    def get_form_kwargs(self):
        """
        Set owner initial in filter form
        """
        kwargs = super().get_form_kwargs()
        user_id = self.request.GET.get('user', None)
        if user_id:
            user = self.get_client_action('get_user')(user_id)
            kwargs.update({
                'user': [[user['id'], user['full_name']]],
            })
        return kwargs

    @staticmethod
    def edit_filter_params(cleaned_data):
        """
        Edits date parameters to match api format.
        """
        if 'added_from' in cleaned_data and cleaned_data['added_from']:
            cleaned_data['added_from'] = cleaned_data['added_from'].strftime("%Y-%m-%d")
        if 'added_to' in cleaned_data and cleaned_data['added_to']:
            cleaned_data['added_to'] = cleaned_data['added_to'].strftime("%Y-%m-%d")
        return cleaned_data


class PhotoUploadListView(BaseListView):
    template_name = 'bima_back/logs/photo_upload_log.html'
    lookup_object = 'logs'
    action_name = 'get_photo_upload_log_list'


class FilteredPhotoListBaseView(BaseListView):
    """
    Base for views that list photos with a filter, such as status or owner.
    user for public album view and personal photos view.
    """
    template_name = 'bima_back/photos/filtered_list.html'
    lookup_object = 'photos'
    action_name = 'get_photos_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': self.get_title(),
            'page_breadcrumbs': self.get_breadcrumbs(),
        })
        return context

    @staticmethod
    def get_breadcrumbs():
        return ''

    @staticmethod
    def get_title():
        return ''


class AlbumPublicListView(FilteredPhotoListBaseView):
    """
    View to list all public photos
    """
    active_section = 'album'

    def add_params(self, params):
        params.update({'status': 1})
        return params

    @staticmethod
    def get_title():
        return _('Public Album')

    @staticmethod
    def get_breadcrumbs():
        return [
            {'label': _('Home'), 'view': 'home'},
            {'label': _('Albums'), 'view': 'album_list'},
            {'label': _('Public Album'), 'view': 'album_public_list'}
        ]


class MyPhotosListView(FilteredPhotoListBaseView):
    """
    View to list photos of the current user
    """
    active_section = 'my_photos'

    def add_params(self, params):
        params.update({'owner': self.request.user.id})
        return params

    @staticmethod
    def get_title():
        return _('My Assets')

    @staticmethod
    def get_breadcrumbs():
        return [
            {'label': _('Home'), 'view': 'home'},
            {'label': _('My Assets'), 'view': 'my_photos_list'}
        ]


# create views

class BaseCreateView(LoggedServiceMixin, FormView):
    """
    Base view to create new instances
    """
    template_name = 'bima_back/create_update.html'
    instance = None
    active_section = ''
    title = ''

    def do_form_valid_action(self, data, form):
        return self.get_client_action()(data)

    def form_valid(self, form):
        data = {}
        for key in form.cleaned_data.keys():
            data[key] = form.cleaned_data.get(key)
        data = self.edit_params(data)
        self.do_form_valid_action(data, form)
        return super().form_valid(form)

    def edit_params(self, data):
        return data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'instance': self.instance,
            'active_section': self.active_section,
            'page_breadcrumbs': self.get_breadcrumbs(),
            'title': self.get_title()
        })
        return context

    def get_title(self):
        return self.title

    def get_breadcrumbs(self):
        return ''


class AlbumCreateView(BaseCreateView):
    form_class = AlbumForm
    success_url = reverse_lazy('album_list')
    action_name = 'create_album'
    active_section = 'album'
    title = _('Create album')

    def get_breadcrumbs(self):
        return [{'label': _('Albums'), 'view': 'album_list'}, {'label': _('Create'), 'view': 'album_create'}]


class PhotoCreateMultipleView(BaseCreateView):
    template_name = 'bima_back/photos/photo_create_multiple.html'
    form_class = PhotoCreateForm
    success_url = reverse_lazy('photo_list')
    action_name = 'get_client_schema'  # action to get client schema
    active_section = 'upload'
    title = _('Create')
    form_valid_message = _("Your assets have been uploaded successfully and are being processed. "
                           "If you don't see them yet, try to reload the browser in a few seconds.")

    def get_context_data(self, **kwargs):
        """
        Add form to import photo from flickr
        """
        context = super().get_context_data(**kwargs)
        context['flickr_enabled'] = settings.FLICKR_ENABLED
        context['flickrForm'] = FlickrForm()
        context['form_class'] = 'wide-form'
        return context

    def do_form_valid_action(self, data, form):
        """
        Start upload task for each photo submitted
        """
        params = {'keywords': prepare_keywords(data)}
        photos_ids = data['upload_id'].split(',')
        for photo in photos_ids:
            if photo:
                params.update({
                    'album': data['album'],
                    'upload_id': photo,
                    'exif_date': "{}T00:00".format(data['exif_date'].isoformat()) if data['exif_date'] else None,
                    'author': data['author'],
                    'copyright': data['copyright'],
                    # date of the entry of the photo in the system
                    'categorize_date': format_date(datetime.now(), final="%Y-%m-%d", isoformat=False)
                })

                # i18n fields
                for lang_code, _lang_name in settings.LANGUAGES:
                    title_key = 'title_{}'.format(lang_code)
                    params[title_key] = data.get(title_key, '')
                    desc_key = 'description_{}'.format(lang_code)
                    params[desc_key] = data.get(desc_key, '')

                upload_photo.delay(params, self.request.user.id, self.request.user.token,
                                   self.request.LANGUAGE_CODE)

    def get_breadcrumbs(self):
        return [{'label': _('Upload'), 'view': 'photo_create'}]


class AlbumPhotoCreateMultipleView(PhotoCreateMultipleView):
    """
    Create multiple photos in a preselected album
    """
    form_class = AlbumPhotoCreateForm
    active_section = 'album'

    def get_context_data(self, **kwargs):
        """
        Add form to import photo from flickr to the album
        """
        context = super().get_context_data(**kwargs)
        context.update({
            'flickrForm': AlbumFlickrForm(),
            'create_to_album': self.kwargs['album'],
        })
        return context

    def edit_params(self, data):
        """
        Add album id to the form data
        """
        data['album'] = self.kwargs['album']
        return data

    def get_success_url(self):
        return reverse_lazy('album_detail', args=[self.kwargs['album']])

    def get_breadcrumbs(self):
        return [{'label': _('Albums'), 'view': 'album_list'},
                {'label': self.request.GET.get('album', ' — '), 'view': 'album_detail', 'args': self.kwargs['album']},
                {'label': _('Upload'), 'view': 'photo_create'}]


class FlickrImportView(BaseCreateView):
    form_class = FlickrForm
    success_url = reverse_lazy('photo_list')
    action_name = 'flickr_import'
    title = _('Create photo')

    def edit_params(self, data):
        """
        Gets flickr id from the submitted flickr url
        """
        data['flickr'] = re.search('/\d+/', data['url']).group(0).replace('/', '')
        data.pop('url')
        return data


class AlbumFlickrImportView(FlickrImportView):
    form_class = AlbumFlickrForm

    def edit_params(self, data):
        """
        Add album id to the form data
        """
        super().edit_params(data)
        data['id'] = self.kwargs['album']
        return data

    def get_success_url(self):
        return reverse_lazy('album_detail', args=[self.kwargs['album']])


class PhotoChunkedUploadView(ChunkedUploadView):
    model = MyChunkedUpload
    field_name = 'image'

    def get_queryset(self, request):
        """
        Return all queryset without filtering by user
        """
        return self.model.objects.all()

    def get_extra_attrs(self, request):
        """
        Send no user
        """
        return {'user': None}


class PhotoChunkedUploadCompleteView(ChunkedUploadCompleteView):
    model = MyChunkedUpload

    def get_queryset(self, request):
        """
        Return all queryset without filtering by user
        """
        return self.model.objects.all()

    def get_response_data(self, chunked_upload, request):
        message = "{} {}".format(_("You successfully uploaded"), chunked_upload.filename)
        response = {
            'message': message,
            'upload_id': chunked_upload.upload_id,
            'filename': chunked_upload.filename,
        }
        return response


class GalleryCreateView(BaseCreateView):
    form_class = GalleryForm
    success_url = reverse_lazy('gallery_list')
    action_name = 'create_gallery'
    active_section = 'galley'
    title = _('Create gallery')

    def get_breadcrumbs(self):
        return [{'label': _('Galleries'), 'view': 'gallery_list'}, {'label': _('Create'), 'view': 'gallery_create'}]


class CategoryCreateView(BaseCreateView):
    form_class = CategoryForm
    success_url = reverse_lazy('category_list')
    action_name = 'create_category'
    active_section = 'category'
    title = _('Create category')

    def get_breadcrumbs(self):
        return [{'label': _('Categories'), 'view': 'category_list'}, {'label': _('Create'), 'view': 'category_create'}]


# edit views

class BaseEditView(BaseCreateView):
    """
    Base view for edition
    """

    def get_editable_item(self):
        return self.get_client_restore_action()(self.kwargs['pk'])

    def _get_initial_data(self, instance):
        return instance

    def get_initial(self):
        initial_data = super().get_initial()
        self.instance = self.get_editable_item()
        initial_data.update(self._get_initial_data(self.instance))
        return initial_data

    def edit_params(self, data):
        data['id'] = self.kwargs['pk']
        return data


class AlbumEditView(AlbumMixin, BaseEditView):
    form_class = AlbumForm
    restore_action_name = 'get_album'
    action_name = 'update_album'
    active_section = 'album'

    def get_form_kwargs(self):
        """
        Initial values of album owners
        """
        kwargs = super().get_form_kwargs()
        kwargs.update({'owners': get_choices(self.album_owners, text='full_name')})
        return kwargs

    def get_success_url(self):
        return reverse_lazy('album_detail', args=[self.kwargs['pk']])

    def get_breadcrumbs(self):
        return [{'label': _('Albums'), 'view': 'album_list'}, {'label': _('Edit'), 'view': 'album_edit'}]


class PhotoEditView(PhotoMixin, BaseEditView):
    template_name = 'bima_back/photos/photo_edit.html'
    form_class = PhotoEditForm
    restore_action_name = 'get_photo'
    action_name = 'update_photo'
    active_section = 'album'

    def get_initial(self):
        initial_data = super().get_initial()

        # editors can only edit photo galleries if they own the gallery
        user_galleries = self.photo_galleries
        if not self.photo_gallery_permission('write'):
            user_galleries = self.filter_galleries(self.user.id, self.photo_galleries)

        initial_data.update({
            'galleries': [gallery['gallery'] for gallery in user_galleries],
            'names': self.photo_names,
            'exif_date': '',
            'photo_type': self.photo_type_selected[0],
        })
        for code in get_language_codes():
            opts = get_tag_choices(self.photo_keywords, text='tag', language=code)
            initial_data.update({'keywords_{}'.format(code): get_choices_ids(opts)})
        return initial_data

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'album': [self.photo_album_selected, ],
            'author': [self.photo_author_selected, ],
            'copyright': [self.photo_copyright_selected, ],
            'internal_usage_restriction': [self.photo_internal_restriction_selected, ],
            'external_usage_restriction': [self.photo_external_restriction_selected, ],
            'categories': get_choices(self.photo_categories),
            'galleries': get_choices(self.photo_galleries, code='gallery'),
            'names': get_tag_choices(self.photo_names),
        })
        if getattr(settings, 'PHOTO_TYPES_ENABLED', False):
            kwargs.update({
                'photo_type': [self.photo_type_selected, ],
            })
        for code in get_language_codes():
            keywords = 'keywords_{}'.format(code)
            kwargs.update({keywords: get_tag_choices(self.photo_keywords, text='tag', language=code)})

        return kwargs

    def get_success_url(self):
        return reverse_lazy('photo_detail', kwargs={'pk': self.instance['id']})

    def get_context_data(self, **kwargs):
        """
        Before rendering template, the system requests alogger action:
        a photo has been viewed by a user
        """
        context = super().get_context_data(**kwargs)
        if context['instance']['upload_status'] == UploadStatus.uploading:
            raise Http404('Photo is being uploaded.')
        self.get_client().logger_view({'photo': self.kwargs['pk']})
        return context

    def edit_params(self, data):
        """
        Will prepare data to be send by post through API.
        The most important data to prepare is geo-position (latitude, longitude and position) and keywords.
        Is not necessary to prepare Tagged names (nowadays) because it's a selector with values as keys.
        """
        data['id'] = self.kwargs['pk']
        # post photo method doesn't accept galleries parameter
        data.pop('galleries')
        # rest of preparation
        data = prepare_params(data)
        return data

    def do_form_valid_action(self, data, form):
        """
        Do the action defined on 'action_name', create all links between photos and galleries
        and update photo file.
        """

        # update photo galleries
        self.update_photo_galleries(form)

        # update photo file
        data.pop('image')
        upload_id = data.pop('upload_id')
        if upload_id:
            params = {'upload_id': upload_id, 'id': data['id']}
            upload_photo.delay(params, self.request.user.id, self.request.user.token,
                               self.request.LANGUAGE_CODE, create=False)

        # update photo details
        super().do_form_valid_action(data, form)

    @staticmethod
    def filter_galleries(user_id, galleries):
        """
        Returns a list of galleries if the user is its owner
        """
        return [gallery for gallery in galleries if user_id in gallery['owners']]

    def update_photo_galleries(self, form):
        """
        Creates or deletes links between photos and galleries
        """
        initial_galleries = [str(gallery) for gallery in form.initial['galleries']]
        current_galleries = form.cleaned_data.get('galleries')

        create_galleries = [gallery for gallery in current_galleries if gallery not in initial_galleries]
        for new_gallery in create_galleries:
            self.get_client().create_link({
                'gallery': new_gallery, 'photo': self.kwargs['pk']
            })
        # delete galleries is a list with galleries ids
        # we need the id of the link in order to delete it
        # we get in from the info in photo['photo_galleries'] key 'id'
        delete_galleries = [gallery for gallery in initial_galleries if gallery not in current_galleries]
        delete_links = [gallery_info['id'] for gallery_info in form.initial['extra_info']['photo_galleries']
                        if str(gallery_info['gallery']) in delete_galleries]

        for old_link in delete_links:
            self.get_client().delete_link({
                'id': old_link
            })

    def get_breadcrumbs(self):
        return [{'label': _('Albums'), 'view': 'album_list'},
                {'label': self.instance['extra_info']['album']['title'],
                 'view': 'album_detail',
                 'args': self.instance['album']},
                {'label': _('Update'), 'view': 'photo_edit'}]


class PhotoEditMultipleView(LoggedServiceMixin, FormView):
    """
    View to update several photos at the same time, adding or overriding content
    """
    template_name = 'bima_back/photos/photo_edit_multiple.html'
    form_class = PhotoEditMultipleForm
    success_url = reverse_lazy('photo_list')
    active_section = 'photo'

    def form_valid(self, form):
        editable_photos = self.request.session['cart'].keys()

        # create galleries links
        links = form.cleaned_data.pop('galleries', [])
        for link in links:
            for photo in editable_photos:
                self.get_client().create_link({
                    'gallery': link, 'photo': photo
                })

        # get fields with new content
        cleaned_data = {}
        for key, value in form.cleaned_data.items():
            if value:
                cleaned_data[key] = value

        cleaned_data = prepare_params(cleaned_data)

        # update every photo
        if cleaned_data:
            # categorize date
            cleaned_data['categorize_date'] = format_date(datetime.now(), final="%Y-%m-%d", isoformat=False)
            for photo in editable_photos:
                cleaned_data['id'] = photo
                self.get_client().update_photo_multiple(cleaned_data)

        # delete session cart
        self.request.session['cart'] = {}
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_section'] = self.active_section
        return context


class PhotoEditTagsRedirectView(LoggedServiceMixin, RedirectView):
    permanent = False
    pattern_name = 'photo_detail'
    restore_action_name = 'get_photo'

    def get_redirect_url(self, *args, **kwargs):
        editable_photos = self.request.session['cart'].keys()
        selected_photo = self.get_client_restore_action()(self.kwargs['pk'])
        data = {
            'keywords': selected_photo['keywords'],
            'categories': selected_photo['categories'],
            'names': selected_photo['names'],
        }
        for photo in editable_photos:
            data['id'] = photo
            self.get_client().update_photo_multiple(data)
        messages.success(self.request, _("Your transaction completed successfully."))
        return super(PhotoEditTagsRedirectView, self).get_redirect_url(*args, **kwargs)


class GalleryEditView(GalleryMixin, BaseEditView):
    form_class = GalleryForm
    restore_action_name = 'get_gallery'
    action_name = 'update_gallery'
    active_section = 'gallery'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'owners': get_choices(self.gallery_owners, text='full_name')})
        return kwargs

    def get_success_url(self):
        return reverse_lazy('gallery_detail', args=[self.kwargs['pk']])

    def get_breadcrumbs(self):
        return [{'label': _('Galleries'), 'view': 'gallery_list'}, {'label': _('Edit'), 'view': 'gallery_edit'}]


class CategoryEditView(CategoryMixin, BaseEditView):
    form_class = CategoryForm
    success_url = reverse_lazy('category_list')
    restore_action_name = 'get_category'
    action_name = 'update_category'
    active_section = 'category'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        initial = kwargs['initial']
        if initial['extra_info']['parent']:
            kwargs.update({
                'parent': [(self.category_parent_id, self.category_parent_title), ]
            })
        return kwargs

    def get_breadcrumbs(self):
        return [{'label': _('Categories'), 'view': 'category_list'}, {'label': _('Edit'), 'view': 'category_edit'}]


class CoverBase(ServiceClientMixin, TemplateView):
    """
    Base for views where we select a photo cover for an album or a gallery
    """
    template_name = 'bima_back/cover_confirm.html'
    editable_item_action = None
    cover_item_action = 'get_photo'
    action_name = None
    reverse_url = None
    active_section = ''

    def get_editable_item(self):
        return self.get_client_restore_action(action=self.editable_item_action)(self.kwargs['pk'])

    def get_cover_item(self):
        """
        Gets the photo selected to be the cover
        """
        return self.get_client_restore_action(action=self.cover_item_action)(self.kwargs['cover'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        editable_item = self.get_editable_item()
        context.update({
            'editable_item': editable_item,
            'cover_item': self.get_cover_item(),
            'active_section': self.active_section,
            'page_breadcrumbs': self.get_breadcrumbs(editable_item['title']),
        })
        return context

    def post(self, request, *args, **kwargs):
        """
        Post to update the item and set the cover
        """
        params = {
            'id': self.kwargs['pk'],
            'cover': self.kwargs['cover']
        }
        self.get_client_action()(params)
        return redirect(reverse(self.reverse_url, args=[self.kwargs['pk']]))

    def get_breadcrumbs(self, title):
        return ''


class AlbumCoverView(CoverBase):
    template_name = 'bima_back/cover_confirm.html'
    editable_item_action = 'get_album'
    action_name = 'update_album'
    reverse_url = 'album_detail'
    active_section = 'album'

    def get_breadcrumbs(self, title):
        return [{'label': _('Albums'), 'view': 'album_list'},
                {'label': title, 'view': 'album_detail', 'args': self.kwargs['pk']},
                {'label': _('Set Cover'), 'view': 'album_cover'}]


class GalleryCoverView(CoverBase):
    template_name = 'bima_back/cover_confirm.html'
    editable_item_action = 'get_gallery'
    action_name = 'update_gallery'
    reverse_url = 'gallery_detail'
    active_section = 'gallery'

    def get_breadcrumbs(self, title):
        return [{'label': _('Galleries'), 'view': 'gallery_list'},
                {'label': title, 'view': 'gallery_detail', 'args': self.kwargs['pk']},
                {'label': _('Set Cover'), 'view': 'gallery_cover'}]


# delete views

class BaseDeleteView(LoggedServiceMixin, TemplateView):
    """
    Base view to delete objects
    """
    template_name = 'bima_back/delete.html'
    url_name = 'home'
    active_section = ''
    title = ''

    def get_object_to_delete(self):
        self.instance = self.get_client_restore_action()(self.kwargs['pk'])

    def post(self, request, *args, **kwargs):
        self.get_client_action()(self.kwargs['pk'])
        return redirect(reverse(self.url_name))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.get_object_to_delete()
        context.update({
            'object': self.instance,
            'title': self.get_title,
            'active_section': self.active_section,
            'page_breadcrumbs': self.get_breadcrumbs()
        })
        return context

    def get_title(self):
        return self.title

    def get_breadcrumbs(self):
        return ''


class AlbumDeleteView(BaseDeleteView):
    restore_action_name = 'get_album'
    action_name = 'delete_album'
    url_name = 'album_list'
    active_section = 'album'
    title = _('Are you sure you want to delete this album?')

    def get_breadcrumbs(self):
        return [{'label': _('Albums'), 'view': 'album_list'}, {'label': _('Delete'), 'view': 'album_delete'}]


class PhotoDeleteView(BaseDeleteView):
    restore_action_name = 'get_photo'
    action_name = 'delete_photo'
    url_name = 'photo_list'
    active_section = 'album'
    title = _('Are you sure you want to delete this asset?')

    def get_breadcrumbs(self):
        return [{'label': _('Albums'), 'view': 'album_list'},
                {'label': self.instance['extra_info']['album']['title'],
                 'view': 'album_detail',
                 'args': self.instance['album']},
                {'label': _('Delete'), 'view': 'photo_delete'}]


class PhotoEditYoutubeView(BaseDeleteView):
    """
    Show a list of Youtube channels and then upload the video to the choosen channel.

    The flow is similar to a DeleteView but nothing is deleted.
    """
    template_name = 'bima_back/photos/photo_edit_youtube.html'
    restore_action_name = 'youtube_channels'
    action_name = 'youtube_upload'
    url_name = 'photo_list'
    active_section = 'album'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = YoutubeChannelForm(self.instance['youtube_channels'])
        context['column_class'] = 'col-md-12'
        return context

    def get_breadcrumbs(self):
        return [{'label': _('Albums'), 'view': 'album_list'},
                {'label': self.instance['photo']['album']['title'],
                 'view': 'album_detail',
                 'args': self.instance['photo']['album']['id']},
                {'label': _('Youtube'), 'view': 'photo_edit_youtube'}]

    def get_title(self):
        return _('Select Youtube channel to upload video "{}"'.format(
                 self.instance['photo']['title']))

    def post(self, request, *args, **kwargs):
        self.get_client_action()(kwargs['pk'], request.POST['youtube_channel'])
        msg = _('Video has been enqueued to be uploaded to Youtube. It can take a while to complete.')
        messages.success(request, msg)
        return redirect(reverse(self.url_name))


class PhotoEditVimeoView(BaseDeleteView):
    """
    Show a list of Vimeo accounts and then upload the video to the choosen account.

    The flow is similar to a DeleteView but nothing is deleted.
    """
    template_name = 'bima_back/photos/photo_edit_youtube.html'
    restore_action_name = 'vimeo_accounts'
    action_name = 'vimeo_upload'
    url_name = 'photo_list'
    active_section = 'album'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = VimeoAccountForm(self.instance['vimeo_accounts'])
        context['column_class'] = 'col-md-12'
        return context

    def get_breadcrumbs(self):
        return [{'label': _('Albums'), 'view': 'album_list'},
                {'label': self.instance['photo']['album']['title'],
                 'view': 'album_detail',
                 'args': self.instance['photo']['album']['id']},
                {'label': _('Vimeo'), 'view': 'photo_edit_vimeo'}]

    def get_title(self):
        return _('Select Vimeo account to upload video "{}"'.format(
                 self.instance['photo']['title']))

    def post(self, request, *args, **kwargs):
        self.get_client_action()(kwargs['pk'], request.POST['vimeo_account'])
        msg = _('Video has been enqueued to be uploaded to Vimeo. It can take a while to complete.')
        messages.success(request, msg)
        return redirect(reverse(self.url_name))


class GalleryDeleteView(BaseDeleteView):
    restore_action_name = 'get_gallery'
    action_name = 'delete_gallery'
    url_name = 'gallery_list'
    active_section = 'gallery'
    title = _('Are you sure you want to delete this gallery?')

    def get_breadcrumbs(self):
        return [{'label': _('Galleries'), 'view': 'gallery_list'}, {'label': _('Delete'), 'view': 'gallery_delete'}]


class CategoryDeleteView(BaseDeleteView):
    restore_action_name = 'get_category'
    action_name = 'delete_category'
    url_name = 'category_list'
    active_section = 'category'
    title = _('Are you sure you want to delete this category?')

    def get_breadcrumbs(self):
        return [{'label': _('Categories'), 'view': 'category_list'}, {'label': _('Delete'), 'view': 'category_delete'}]


# detail views

class BaseDetailView(LoggedServiceMixin, TemplateView):
    """
    Base view to show detailed information
    """
    template_name = 'bima_back/detail.html'
    lookup_title = 'title'
    active_section = ''

    def get_object(self):
        return self.get_client_restore_action()(self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        # get object information from service client
        self.instance = self.get_object()
        # get context and update with results from service
        context = super().get_context_data(**kwargs)
        context.update({
            'instance': self.instance,
            'instance_title': self.instance.get(self.lookup_title, get_class_name(self))
        })
        context['active_section'] = self.active_section
        return context


class PhotoDetailView(BaseDetailView):
    template_name = 'bima_back/photos/photo_detail.html'
    restore_action_name = 'get_photo'
    active_section = 'album'

    def get_context_data(self, **kwargs):
        """
        Before rendering template, the system requests logger action:
        a photo will be downloaded by a user
        """
        context = super().get_context_data(**kwargs)
        if context['instance']['upload_status'] == UploadStatus.uploading:
            raise Http404('Photo is being uploaded.')

        self.get_client().logger_view({'photo': self.kwargs['pk']})
        context.update({
            'google_maps_api_key': settings.GEOPOSITION_GOOGLE_MAPS_API_KEY,
            'photo_detail_page': True,
        })
        return context


class DetailWithPhotoBase(PaginatorMixin, BaseDetailView):
    """
    Base view to show information and the list of photos of this album or gallery
    """
    filter_photo_field = None

    def get_filter_field(self):
        if not self.filter_photo_field:
            raise NotImplementedError
        return self.filter_photo_field

    def get_photo_list(self):
        """
        Get list of photos, filtering by album or gallery and page
        """
        filters = {
            self.get_filter_field(): self.instance.get('id'),
            'page': self.get_current_page()
        }
        return self.get_client().get_photos_list(**filters)

    def get_context_data(self, **kwargs):
        """
        Before rendering template, requests information about photos of the current album
        """
        context = super().get_context_data(**kwargs)
        response = self.get_photo_list()
        context.update({
            'page': self.paginate(response['count'], response['per_page']),
            'photo_list': response['results']
        })
        return context


class AlbumDetailView(DetailWithPhotoBase):
    template_name = 'bima_back/albums/album_detail.html'
    restore_action_name = 'get_album'
    filter_photo_field = 'album'
    active_section = 'album'


class GalleryDetailView(DetailWithPhotoBase):
    template_name = 'bima_back/galleries/gallery_detail.html'
    restore_action_name = 'get_gallery'
    filter_photo_field = 'gallery'
    active_section = 'gallery'


# logger register view and download photo


class PhotoDownloadLogView(LoggedServiceMixin, View):

    def get(self, request, *args, **kwargs):
        raise NotImplementedError

    def post(self, request, *args, **kwargs):
        """
        Post to register when a user downloads a photo
        """
        self.get_client().logger_download({'photo': self.kwargs['pk']})
        return JsonResponse(data="", safe=False)


# create, edit and delete users

class UserCreateView(BaseCreateView):
    template_name = 'bima_back/users/user_form.html'
    form_class = UserForm
    success_url = reverse_lazy('home')
    action_name = 'user_create'


class UserManageView(BaseListView):
    template_name = 'bima_back/users/user.html'
    lookup_object = 'users'
    action_name = 'get_users_list'


class UserEditView(BaseEditView):
    template_name = 'bima_back/users/user_form.html'
    form_class = UserForm
    success_url = reverse_lazy('user_manage')
    restore_action_name = 'get_user'
    action_name = 'user_edit'

    def get_editable_item(self):
        return self.get_client_restore_action()(self.kwargs['pk'])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        groups = get_choices(self.get_client().get_groups_list()['results'], 'id', 'name')
        kwargs.update({'groups': groups})
        return kwargs

    def get_initial(self):
        initial_data = super().get_initial()
        group = initial_data['groups']
        initial_data['groups'] = group[0] if group else None
        return initial_data

    def do_form_valid_action(self, data, form):
        super().do_form_valid_action(data, form)
        self.reset_user_info_cache(data)

    def edit_params(self, data):
        data['id'] = self.kwargs['pk']
        data['groups'] = list(data['groups'])
        return data

    def reset_user_info_cache(self, data):
        """
        After editing a user, reset the cached information
        """
        cache_key = "{}_{}".format(CACHE_USER_PROFILE_PREFIX_KEY, self.request.user.id)
        user_params = cache.get(cache_key)
        user_params.update({'first_name': data['first_name'], 'last_name': data['last_name']})
        cache_set(cache_key, user_params)

    def get_breadcrumbs(self):
        return [{'label': _('Manage Users'), 'view': 'user_manage'}, {'label': _('Edit'), 'view': 'user_edit'}]


class UserDeleteView(BaseDeleteView):
    restore_action_name = 'get_user'
    action_name = 'delete_user'
    url_name = 'user_manage'
    title = _('Are you sure you want to deactivate this user?')

    def get_breadcrumbs(self):
        return [{'label': _('Manage Users'), 'view': 'user_manage'}, {'label': _('Deactivate'), 'view': 'user_delete'}]


class UserActiveView(BaseDeleteView):
    """
    View to active a user again. We use BaseDeleteView because its functionalities are
    enough for this. We don't need BaseEditView methods.
    """
    restore_action_name = 'get_user'
    action_name = 'user_edit'
    url_name = 'user_manage'
    title = _('Are you sure you want to activate this user?')

    def post(self, request, *args, **kwargs):
        self.get_client_action()({'id': self.kwargs['pk'], 'is_active': True})
        return redirect(reverse(self.url_name))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def get_breadcrumbs(self):
        return [{'label': _('Manage Users'), 'view': 'user_manage'}, {'label': _('Activate'), 'view': 'user_active'}]
