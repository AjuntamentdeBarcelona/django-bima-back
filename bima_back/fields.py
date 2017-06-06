# -*- coding: utf-8 -*-
from django import forms
from django.urls import reverse
from django_select2.forms import HeavySelect2Widget, HeavySelect2MultipleWidget, HeavySelect2TagWidget

from .utils import get_language_codes
from .constants import AUTOCOMPLETE_DEFAULT_MIN_LENGTH


class TextField(forms.CharField):
    """
    Charfield with textarea widget
    """
    widget = forms.Textarea


class Select2Field(forms.CharField):
    """
    Field for autocomplete select
    """
    widget = HeavySelect2Widget

    def __init__(self, data_view, min_length=None, *args, **kwargs):
        self._min_length = min_length or AUTOCOMPLETE_DEFAULT_MIN_LENGTH
        if isinstance(self.widget, type):
            self.widget = self.widget(data_view=data_view)
        super().__init__(*args, **kwargs)

    def widget_attrs(self, widget):
        """
        Set minimum char length to start the autocomplete
        """
        widget_attr = super().widget_attrs(widget)
        widget_attr.update({'data-minimum-input-length': self._min_length})
        return widget_attr


class Select2MultipleField(Select2Field):
    """
    Field for autocomplete select multiple
    """
    widget = HeavySelect2MultipleWidget

    def to_python(self, value):
        """ Force to return a list """
        if value in self.empty_values:
            return []
        return value


class Select2TagField(Select2MultipleField):
    """
    Field for autocomplete select multiple tag
    """
    widget = HeavySelect2TagWidget

    def widget_attrs(self, widget):
        widget_attr = super().widget_attrs(widget)
        widget_attr.update({'data-token-separators': '[","]'})
        return widget_attr


class Select2MultilangTagField(Select2TagField):
    """
    Field for autocomplete select multiple tag multilang
    """

    def __init__(self, data_view, min_length=None, language=None, *args, **kwargs):
        data_url = reverse(data_view)
        if language in get_language_codes():
            data_url += "?language={}".format(language)

        self._min_length = min_length or AUTOCOMPLETE_DEFAULT_MIN_LENGTH
        self.widget = self.widget(data_url=data_url)
        super().__init__(data_view, min_length, *args, **kwargs)
