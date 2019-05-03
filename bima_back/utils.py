# -*- coding: utf-8 -*-
from datetime import datetime
import logging
from itertools import groupby
from operator import itemgetter

from django.conf import settings
from django.core.cache import cache
from django.utils.translation import ugettext as _

from bima_back.constants import NOT_ASSIGNED_CHOICES

logger = logging.getLogger(__name__)


def get_choices(items, code='id', text='title', has_unassigned=False):
    """
    Returns tuples to use in form selects
    :param items: expected a list of dictionaries
    :param code: dict-key to define the key of options
    :param text: dict-key to define the value of options
    :param has_unassigned: define if unassigned option allowed
    """
    choices = []
    if items:
        choices = [(item.get(code), item.get(text, '--')) for item in items]
    if has_unassigned:
        choices = choices + NOT_ASSIGNED_CHOICES
    return choices


def get_tag_choices(items, code=None, text=None, language=None):
    """
    Returns tuples to use in form selects
    :param items: expected a list of dictionaries
    :param code: dict-key to define the key of options. If is not defined use 'text' as dict-key.
    :param text: dict-key to define the value of options
    :param language: dict-key to grouping with
    """
    if not items:
        return []

    tag_initials = []
    for info in items:
        key = value = info
        if isinstance(info, dict) and text:
            if not language or info.get('language') != language:
                continue
            key, value = info.get(code or text), info.get(text, '--')
        tag_initials.append((key, value))
    return tag_initials


def get_choices_ids(choices):
    """
    Returns keys of choices to initialize selectors
    :param choices: expected a well formatted choices (list or tuple of <key, value> element)
    """
    if not is_iterable(choices):
        return []
    return [key for key, value in choices]


def get_class_name(instance):
    return str(instance.__class__.__name__).lower()


def get_languages(codes=True, names=True):
    """
    Returns language definition in settings ( codes and name set to True),
    or a list of all language codes (names set to false),
    or a list with all language names (codes set to false)
    """
    if codes == names:
        return settings.LANGUAGES
    return [language[0 if codes else 1] for language in settings.LANGUAGES]


def get_language_codes():
    """
    Returns a list wit the language codes
    """
    return get_languages(names=False)


def order_keywords(keywords):
    """
    Returns keywords grouped by languages
    """
    ordered_keywords = {}
    for code in get_language_codes():
        ordered_keywords["keywords_{}".format(code)] = ""
    keywords = sorted(keywords, key=itemgetter('language'))
    for key, value in groupby(keywords, itemgetter('language')):
        ordered_keywords["keywords_{}".format(key)] = ", ".join(item.get('tag') for item in value)
    return ordered_keywords


def is_iterable(obj):
    """
    Returns true if obj is a list or tuple
    """
    return isinstance(obj, list) or isinstance(obj, tuple)


def get(item, attrs, default='', splitter='.'):
    attrs = attrs.split(splitter)
    for attr in attrs:
        if isinstance(item, dict):
            item = item.get(attr, {})
        else:
            item = getattr(item, attr, None)
    return item or default


def format_date(date_time, original='', final='', isoformat=True):
    """
    Changes format of a date string
    """
    if not isinstance(date_time, datetime):
        try:
            date_time = datetime.strptime(date_time, original or "%d/%m/%Y %H:%M")
        except (ValueError, TypeError):
            return None
    if isoformat:
        return date_time.isoformat()
    return date_time.strftime(final or "%Y-%m-%dT%H:%M:%S")


def popover_string(width, height):
    """
    Prepare the string to inform about the width and height of a photo
    """
    popover = ""
    popover_width = "{}: {}px ".format(_('Width'), width)
    popover_height = "{}: {}px ".format(_('Height'), height)
    if width and height:
        popover = popover_width + popover_height
    elif width:
        popover = popover_width
    elif height:
        popover = popover_height
    return popover


def rule_of_three(multiple1, multiple2, divider):
    """
    Calculation of a missing value in a known relation
    """
    return int(round((multiple1 * multiple2) / divider))


def calculate_missing_size(original_width, original_height, width=0, height=0):
    """
    Function to calculate width or height of a photo if the value is missing in the thumbor url,
    providing that we know the original size of the photo
    """
    value = 0
    if original_width and original_height:
        if height:
            # url has height but no width
            value = rule_of_three(original_width, height, original_height)
        elif width:
            # url has width but no height
            value = rule_of_three(original_height, width, original_width)
    return value


def prepare_keywords(data):
    """
    Returns a list of keywords as dictionaries with lang, tag keys
    """
    keywords = []
    for code in get_language_codes():
        for tag in data.pop("keywords_{}".format(code), ''):
            if tag:
                keywords.append({'language': code, 'tag': tag})
    return keywords


def prepare_position(data, joiner=','):
    """
    :param data: form data
    :param joiner: separator of lat - lon in position data
    :return: latitude, longitude, position
    """
    position = data.get('position', None)
    if not position:
        return 0, 0, None
    position = [str(pos) for pos in position]
    position.append(joiner.join(position))
    return position


def prepare_params(data):
    """
    Prepare parameters when editing one or multiple photos
    """
    # prepare position, latitude and longitude for exif
    if 'position' in data:
        lat, lon, position = prepare_position(data)
        data.update({'latitude': lat, 'longitude': lon, 'position': position})
    # multi-language keywords
    has_keywords = False
    for code in get_language_codes():
        key = "keywords_{}".format(code)
        if key in data:
            has_keywords = True
    if has_keywords:
        data['keywords'] = prepare_keywords(data)
    # exif date
    if 'exif_date' in data and data['exif_date']:
        data['exif_date'] = "{}T00:00".format(data['exif_date'].isoformat())
    return data


def change_form_tag_languages(q_filter):
    """
    Returns the text replacing every tag mapped in LANGUAGE_SEARCH_FORM_TAGS.
    Used for the photo filter form q input.
    """
    separator = ':'
    for tag, localized_tag in settings.LANGUAGE_SEARCH_FORM_TAGS.items():
        q_filter = q_filter.replace(localized_tag + separator, tag + separator)
    return q_filter


# Actuation with default django cache

def is_available_cache():
    cache_backend = settings.CACHES.get('default', {}).get('BACKEND', '')
    return settings.CACHE_ENABLED and 'dummycache' not in cache_backend.lower()


def cache_set(key, value, timeout=None):
    if is_available_cache():
        if timeout:
            cache.set(key, value, timeout)
        else:
            cache.set(key, value)


def cache_delete_startswith(key):
    if is_available_cache():
        cache.delete_many(cache.keys("{}*".format(key)))


# Decorator to analyze performance

def timer_performance(func):
    """
    Decorator to measure elapse time of function which decorate
    """
    def _wrapped_function(*args, **kwargs):
        import time
        start = time.time()
        response = func(*args, **kwargs)
        logger.debug("***[{}]: Elapsed {}s".format(func.__name__, time.time() - start))
        return response
    return _wrapped_function
