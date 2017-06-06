# -*- coding: utf-8 -*-
from bima_back.models import PhotoFilter
from bima_back.photo_filters.forms import AddFilterForm
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.generic.base import View


class AddFilter(View):
    """
    Creates a new photo filter
    """

    def get(self, request, *args, **kwargs):
        values = {
            'name': self.request.GET.get('name', ''),
            'filter': self.request.GET.get('filter', ''),
            'username': self.request.user.username,
        }
        form = AddFilterForm(values)
        if form.is_valid():
            form.save()
        else:
            return JsonResponse(data=None, safe=False, status=500)

        context = {
            'filters': PhotoFilter.objects.filter(username=self.request.user.username).order_by('name'),
            'search': True,
        }
        data = render_to_string('bima_back/includes/saved_filters_menu.html', context=context)
        return JsonResponse(data=data, safe=False)


class RemoveFilter(View):
    """
    Removes a photo from the session cart given its id.
    Returns the cart template rendered without this photo.
    """

    def get(self, request, *args, **kwargs):

        try:
            photo_filter = PhotoFilter.objects.get(id=self.kwargs['pk'])
            photo_filter.delete()
        except ObjectDoesNotExist:
            return JsonResponse(data=None, safe=False, status=500)

        context = {
            'filters': PhotoFilter.objects.filter(username=self.request.user.username).order_by('name'),
            'search': True,
        }
        data = render_to_string('bima_back/includes/saved_filters_menu.html', context=context)
        return JsonResponse(data=data, safe=False)
