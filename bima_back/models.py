# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import ugettext as _

from chunked_upload.models import AbstractChunkedUpload

AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'bima_back.DAMUser')


class DAMUser(AbstractUser):
    token = models.CharField(_('token'), max_length=100, blank=True)
    dam_groups = models.CharField(_('DAM groups'), max_length=100, blank=True)
    admin = models.BooleanField(_('admin'), default=False)
    permissions = models.TextField(_('permissions'), blank=True)

    def save(self, *args, **kwargs):
        if kwargs.get('force_insert', False):
            super(AbstractUser, self).save(*args, **kwargs)


class MyChunkedUpload(AbstractChunkedUpload):
    user = models.ForeignKey(AUTH_USER_MODEL, verbose_name=_('user'), related_name='my_chunked_uploads', null=True,
                             on_delete=models.RESTRICT)

    class Meta:
        verbose_name = _('My chunked upload')
        verbose_name_plural = _('My chunked uploads')


class PhotoFilter(models.Model):
    username = models.CharField(max_length=150, verbose_name=_('Username'))
    name = models.CharField(max_length=60, verbose_name=_('Name'))
    filter = models.TextField(verbose_name=_('Filter'))

    class Meta:
        verbose_name = _('Photo filter')
        verbose_name_plural = _('Photo filters')
        ordering = ('username', )
