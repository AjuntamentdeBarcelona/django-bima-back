# -*- coding: utf-8 -*-
import logging
from os.path import splitext
import re
import six
from bima_back.models import PhotoFilter

from constance import config
from django.templatetags.static import static
from django.conf import settings
from django.urls import resolve, reverse
from django.forms.widgets import CheckboxInput, RadioSelect
from django.template import Library
from django.template.defaultfilters import stringfilter, slugify, truncatechars
from django.utils.dateparse import parse_datetime, parse_date
from django.utils.html import mark_safe
from django.utils.translation import activate, get_language

from ..utils import get_class_name, order_keywords, is_iterable, calculate_missing_size, popover_string


register = Library()
logger = logging.getLogger(__name__)


@register.filter
@register.simple_tag
def settings_value(name):
    """
    Returns a value from the settings
    """
    return getattr(settings, name, "")


@register.simple_tag
def constance_value(name):
    """
    Returns a value from constance configuration
    """
    return getattr(config, name, "")


@register.simple_tag(takes_context=True)
def verbose_object_name(context, instance=None):
    """
    Its a formatter method to get the base name to show in each page according the url action. Moreover, if an
    object is defined concat its 'name', 'title' or 'username' value field to the verbose name.
    :return: string name of each page section
    """
    tag_matches = ('_', 'list', 'create', 'update', 'edit', 'delete', 'reset', 'change', 'detail', 'cover', 'active', )
    url_name = context['view'].request.resolver_match.url_name
    verbose_name = re.sub(r"({})".format("|".join(tag_matches)), '', url_name)
    # instance data as dict is defined
    if instance:
        object_name = instance.get('title') or instance.get('name') or instance.get('username')
        verbose_name = "{}: {}".format(verbose_name, object_name)
    return verbose_name


@register.simple_tag(takes_context=True)
def change_language(context, language=None, *args, **kwargs):
    """
    Get active page's url by a specified language
    Usage: {% change_language 'en' %}
    """
    try:
        current_language = get_language()
        path = context['request'].path
        url_parts = resolve(path)
        activate(language)
        url = reverse(url_parts.view_name, kwargs=url_parts.kwargs)
    except Exception as e:
        logger.error("Error trying to change language {} to {}\n{}".format(current_language, language, e))
        url = reverse("404")
    finally:
        activate(current_language)
    return "%s" % url if url != "/" else "%s%s" % (url, language)


@register.filter
@register.simple_tag
def class_name(value):
    return get_class_name(value)


@register.filter
@stringfilter
def split(value, arg=','):
    """
    Split the string of 'value' parameter with the key of 'arg' parameter.
    :return: List of strings as a result of split the original.
    """
    return value.split(arg)


@register.filter
def select_form_fields(form, field_names):
    """
    :parameter field_names: List of field names.
    :return: a list of field to represent in the form according 'field_names' parameter.
    """
    if is_iterable(field_names) and len(field_names) > 0:
        return [field for field in form if field.name in field_names]
    return []


@register.filter
def discard_form_fields(form, field_names):
    """
    :parameter field_names: List of field names which will be excluded.
    :return: a list of field to represent in the form excluding all of 'field_names' parameter.
    """
    if is_iterable(field_names) and len(field_names) > 0:
        return [field for field in form if field.name not in field_names]
    return []


@register.filter
def show_semantic_filter(form, field_names):
    """
    The form to filter photos is divided into two parts a semantic field and a specific field set and each one request
    photos to API using two different endpoints.
    :return: boolean indicating if photo filter form should only show semantic field or only the accurate fields.
    """
    data = getattr(form, 'cleaned_data', form.data)
    for field_name in field_names:
        data.pop(field_name, None)
    return not data


@register.filter
def is_checkbox(field):
    """
    :return: if widget is instance of checkbox.
    """
    # if field is a bound-field
    if hasattr(field, 'field'):
        field = field.field
    return isinstance(field.widget, CheckboxInput)


@register.filter
def is_radio(field):
    """
    :return: if widget is instance of radio select.
    """
    # if field is a bound-field
    if hasattr(field, 'field'):
        field = field.field
    return isinstance(field.widget, RadioSelect)


@register.filter(is_safe=False)
def default_if_blank(value, arg):
    """
    :return: if value is '', use given default.
    """
    return arg if value == '' else value


@register.inclusion_tag('bima_back/categories/item.html')
def children_tag(permission, search, category):
    """
    Tag to render categories child
    """
    return {
        'permission': permission,
        'search': search,
        'children': category,
    }


@register.simple_tag
def get_ordered_keywords(keywords):
    """
    :return: a dictionary with keywords_lang: tags.
    """
    return order_keywords(keywords)


@register.simple_tag
def lang_content(instance, field, lang):
    """
    :return: the field in the required language.
    """
    return instance.get("{}_{}".format(field, lang)) or " — "


@register.simple_tag
def pagination_url(get_params):
    """
    Returns get parameters to use them with a url
    """
    url = ""
    for i, (key, value) in enumerate(get_params.items()):
        union = '&' if i else '?'
        url += "{}{}={}".format(union, key, value)
    return url


@register.simple_tag
def pagination_url_export(get_params):
    """
    Adds export get parameter
    """
    url = pagination_url(get_params)
    union = '&' if url else '?'
    url += "{}export=csv".format(union)
    return url


@register.inclusion_tag('bima_back/includes/pagination/pagination_results.html')
def pagination_render_results(page):
    """
    In charge of render number of elements are showing in the current page
    :param page:
    :return:
    """
    results = {'results': page.paginator.count}
    if page.paginator.count > page.paginator.per_page:
        accumulated_size = (page.number - 1) * page.paginator.per_page

        current_page_size = accumulated_size + page.paginator.per_page
        if page.number == page.paginator.num_pages:
            current_page_size = page.paginator.count

        results.update({'showing': {'first': accumulated_size + 1, 'last': current_page_size}})
    return results


@register.simple_tag
def get_download_dimension(instance, size):
    """
    Returns strings to inform about the photo size. Known from its url
    and from the original size.
    """
    width = instance['width']
    height = instance['height']
    if size != 'image_original' and instance[size]:
        url_size = re.search('\d{1,4}x\d{1,4}', instance[size]).group(0)
        width = int(url_size.split('x')[0])
        height = int(url_size.split('x')[1])
        if not width:
            width = calculate_missing_size(instance['width'], instance['height'], height=height)
        elif not height:
            height = calculate_missing_size(instance['width'], instance['height'], width=width)
    return popover_string(width, height)


@register.simple_tag
def get_download_filename(instance, extension='jpg'):
    """
    Returns the filename after changing the extension
    :param instance: photo instance
    :param extension: final extension
    :return: filename with the new extension
    """
    filename = ""
    original_filename = instance['original_file_name']
    if original_filename:
        name, ext = splitext(original_filename)
    else:
        name = slugify(instance['description']) or slugify(instance['title'])
        name = truncatechars(slugify(name), 50)
    if name:
        filename = "{}.{}".format(name, extension)
    return filename


@register.filter
def thumbor_supports_file(filename):
    """
    :param filename: name of the file to download
    :return: True if the extension is in the thumbor supported extensions setting, False otherwise.
    """
    if filename:
        name, ext = splitext(filename)
        if getattr(settings, 'THUMBOR_SUPPORTED_EXTENSIONS', []) and ext in settings.THUMBOR_SUPPORTED_EXTENSIONS:
            return True
    return False


@register.filter
@register.simple_tag
def image_size(size):
    """
    Render size of image.
    """
    # validation of input
    if isinstance(size, six.string_types):
        try:
            size = int(size)
        except (ValueError, TypeError):
            size = 0
    # select best units to render
    kb = size / 1024.0
    if kb < 1:
        return "{:.2f} Bytes".format(size)
    mb = kb / 1024.0
    if mb < 1:
        return "{:.2f} KB".format(kb)
    return "{:.2f} MB".format(mb)


@register.filter
def to_datetime(value):
    """
    Parses a datetime string and returns a datetime.datetime
    """
    if value:
        return parse_datetime(value)


@register.filter
def to_date(value):
    """
    Parses a date string and returns a datetime.date
    """
    if value:
        return parse_date(value)


@register.simple_tag
def go_back_url(breadcrumbs):
    """
    Returns the url of the previous page based on the breadcrumbs
    """
    try:
        prev_page = breadcrumbs[-2]
    except IndexError:
        return reverse('home')
    args = prev_page.get('args', '')
    if args:
        return reverse(prev_page['view'], args=[args])
    return reverse(prev_page['view'])


@register.simple_tag
def list_pages(page_urls):
    """
    Returns a list with the number of the pages of the paginator
    """
    return [page[0] for page in page_urls]


@register.inclusion_tag('bima_back/includes/search_form_instructions.html')
def render_search_form_instructions():
    """
    Renders instructions for the photo search form
    """
    return {
        'tags': settings.LANGUAGE_SEARCH_FORM_TAGS,
    }


@register.inclusion_tag('bima_back/includes/saved_filters_menu.html')
def saved_filters(username, parameters):
    """
    Renders the list of saved filters
    """
    return {
        'filters': PhotoFilter.objects.filter(username=username).order_by('name'),
        'search': 'q' in parameters,
    }


@register.simple_tag
def photo_thumbnail(photo):
    """
    Returns the thumbnail of the photo based on it's file type
    """
    if photo['image_thumbnail']:
        return photo['image_thumbnail']
    if photo['file_type'] == 'video':
        return static('bima_back/img/video.jpg')
    if photo['file_type'] == 'audio':
        return static('bima_back/img/audio.jpg')
    if photo['file_type'] == 'file':
        return static('bima_back/img/file.jpg')
    return static('bima_back/img/no-photo.jpg')


FONT_AWESOME_CLASS_MAP = {
    'video': 'play-circle-o',
    'audio': 'volume-up',
    'file': 'file',
    # 'photo': 'photo',
}


@register.simple_tag
def photo_file_type_icon(photo):
    """
    Returns the proper icon to show in every photo in lists based on the photo
    file type (video, audio...).
    """
    font_awesome_class = FONT_AWESOME_CLASS_MAP.get(photo['file_type'])
    if font_awesome_class:
        return mark_safe('<i class="fa fa-{} fileType"></i>'.format(font_awesome_class))
    return ''
