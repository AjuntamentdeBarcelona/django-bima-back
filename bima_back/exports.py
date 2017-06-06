# -*- coding: utf-8 -*-
import csv
from datetime import datetime
import io

from django.utils.text import slugify
from django.utils.translation import ugettext as _

from .utils import get


class LogReport(object):
    """
    Generates a csv file with logs of downloaded and visited images
    """
    _format = 'csv'
    _content_type = 'text/csv'

    def __init__(self, data=None, user=None):
        self.named_fields = [
            {'field': 'photo', 'label': _('Photo id')},
            {'field': 'title', 'label': _('Photo title')},
            {'field': 'get_action_display', 'label': _('Action')},
            {'field': 'user.full_name', 'label': _('User')},
            {'field': 'added_at', 'label': _('Added at')},
        ]
        self.file = io.StringIO()
        self.writer = csv.writer(self.file)
        self.data = data or []
        self.username = get(user, 'username', 'anonymous_user')

        self._generate_report()

    @property
    def content_type(self):
        return self._content_type

    @property
    def file_name(self):
        return "{}_{}_{}.{}".format(self.username, slugify(self.__class__), datetime.now().isoformat(), self._format)

    @property
    def titles(self):
        return [named_field['label'] for named_field in self.named_fields]

    @property
    def fields(self):
        return [named_field['field'] for named_field in self.named_fields]

    @property
    def csv(self):
        return self.file.getvalue()

    def _generate_report(self):
        self.writer.writerow(self.titles)
        for item in self.data:
            self.writer.writerow([get(item, field, '') for field in self.fields])
