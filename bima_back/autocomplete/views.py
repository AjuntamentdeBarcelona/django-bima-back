# -*- coding: utf-8 -*-
import logging

from constance import config
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.generic.base import View

from ..mixins import ServiceClientMixin
from ..utils import timer_performance

from .serializers import AutocompleteSerializer


logger = logging.getLogger(__name__)


class BaseSearchView(LoginRequiredMixin, ServiceClientMixin, View):
    http_method_names = ('get', )
    query_param = 'term'
    extra_query_param = ()
    lookup_field = ''
    text_field = ''
    id_field = ''
    response_class = JsonResponse
    paginate_by = 5
    filter_by_user = False

    def get_lookup_field(self):
        if not self.lookup_field:
            raise NotImplementedError
        return self.lookup_field

    def get_action_kwargs(self, page):
        """
        Returns a dictionary with the parameters for the api request
        """
        kwargs = {'page': page, self.lookup_field: self.request.GET.get(self.query_param)}
        # If the user can't create galleries, the autocomplete of galleries will only show the galleries they own.
        # This is for the editors, who can only assign photos to galleries they own.
        if self.filter_by_user and not self.request.user.permissions['gallery']['write']:
            kwargs.update({'owners': self.request.user.id})
        return kwargs

    def get_extra_action_kwargs(self):
        """
        Add extra parameters set as extra_query_param
        """
        if not self.extra_query_param:
            return {}
        return {qparam: self.request.GET.get(qparam) for qparam in self.extra_query_param}

    def get_queryset(self, page=1):
        client_action = self.get_client_action()
        if not client_action:
            return []
        action_kwargs = self.get_action_kwargs(page)
        action_kwargs.update(self.get_extra_action_kwargs())
        return client_action(**action_kwargs)

    def get_paginate_by(self):
        """
        Returns pagination size
        """
        page_size = config.AUTOCOMPLETE_PAGE_SIZE or self.paginate_by
        return page_size if page_size > 0 else 1

    def paginate(self, object_data):
        results, iterations = object_data.get('results', []), 0
        # trivial case: number of results less than page_size
        page_size = self.get_paginate_by()
        if len(object_data.get('results', [])) <= page_size or not object_data.get('next', None):
            return object_data
        # need request more pages
        while len(results) < page_size:
            object_data = self.get_queryset(object_data.get('next'))
            results.extend(object_data.get('results'))
            iterations += 1
            if iterations > config.AUTOCOMPLETE_PAGE_ITERATION:
                logger.warning("Check the server pagination size and the autocomplete pagination size")
        return {'results': results[:page_size]}

    def get_text_field(self):
        """
        Returns the name of the field used as text
        """
        return self.text_field or self.lookup_field

    def get_id_field(self):
        """
        Returns the name of the field used as id
        """
        return self.id_field or 'id'

    def get_serializer(self, data):
        return AutocompleteSerializer(data, text_field=self.get_text_field(), id_field=self.get_id_field(), many=True)

    def render_to_response(self, data):
        serializer = self.get_serializer(data)
        return self.response_class(data={'results': serializer.data})

    @timer_performance
    def get(self, request, *args, **kwargs):
        object_data = self.get_queryset()
        if self.get_paginate_by():
            object_data = self.paginate(object_data)
        object_list = object_data.get('results')
        return self.render_to_response(object_list)


class GroupSearchView(BaseSearchView):
    action_name = 'get_groups_list'
    lookup_field = 'name'


class UserSearchView(BaseSearchView):
    """
    User autocomplete should only search active users
    """
    action_name = 'get_users_list'
    lookup_field = 'full_name'

    def get_extra_action_kwargs(self):
        extra_kwargs = super().get_extra_action_kwargs()
        extra_kwargs.update({'is_active': True})
        return extra_kwargs


class AlbumSearchView(BaseSearchView):
    action_name = 'get_albums_simple_list'
    lookup_field = 'title'
    text_field = 'title'


class PhotoSearchView(BaseSearchView):
    action_name = 'get_photos_list'
    lookup_field = 'title'
    text_field = 'title'


class CategorySearchView(BaseSearchView):
    action_name = 'get_categories_simple_list'
    lookup_field = 'name'
    text_field = 'name'


class GallerySearchView(BaseSearchView):
    action_name = 'get_galleries_simple_list'
    lookup_field = 'title'
    text_field = 'title'
    filter_by_user = True


class NameSearchView(BaseSearchView):
    action_name = 'get_names_list'
    lookup_field = 'tag'
    id_field = 'tag'


class KeywordSearchView(BaseSearchView):
    action_name = 'get_keywords_list'
    lookup_field = 'tag'
    id_field = 'tag'
    extra_query_param = ('language', )


class AuthorSearchView(BaseSearchView):
    action_name = 'get_authors_list'
    lookup_field = 'full_name'


class CopyrightSearchView(BaseSearchView):
    action_name = 'get_copyrights_list'
    lookup_field = 'name'


class RestrictionSearchView(BaseSearchView):
    action_name = 'get_restrictions_list'
    lookup_field = 'title'


class TypeSearchView(BaseSearchView):
    action_name = 'get_photo_type_list'
    lookup_field = 'name'
