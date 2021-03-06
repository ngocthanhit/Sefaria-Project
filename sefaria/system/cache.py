
import hashlib
import sys

try:
    from sefaria.settings import USE_VARNISH
except ImportError:
    USE_VARNISH = False

if not hasattr(sys, '_doc_build'):
    from django.core.cache import cache

# Simple caches for indices, parsed refs, table of contents and texts list
index_cache = {}

#functions from here: http://james.lin.net.nz/2011/09/08/python-decorator-caching-your-functions/
#and here: https://github.com/rchrd2/django-cache-decorator

# New cache instance reconnect-apparently
cache_factory = {}

def get_cache_factory(cache_type):
    """
    Helper to only return a single instance of a cache
    As of django 1.7, may not be needed.
    """
    from django.core.cache import get_cache

    if cache_type is None:
        cache_type = 'default'

    if not cache_type in cache_factory:
        cache_factory[cache_type] = get_cache(cache_type)

    return cache_factory[cache_type]


#get the cache key for storage
def cache_get_key(*args, **kwargs):
    serialise = []
    for arg in args:
        serialise.append(str(arg))
    for key,arg in kwargs.items():
        serialise.append(str(key))
        serialise.append(str(arg))
    key = hashlib.md5("".join(serialise)).hexdigest()
    return key

def django_cache_decorator(time=300, cache_key='', cache_type=None):
    """
    Easily add caching to a function in django
    """
    cache = get_cache_factory(cache_type)
    if not cache_key:
        cache_key = None

    def decorator(fn):
        def wrapper(*args, **kwargs):
            #logger.debug([args, kwargs])

            # Inner scope variables are read-only so we set a new var
            _cache_key = cache_key

            if not _cache_key:
                _cache_key = cache_get_key(fn.__name__, *args, **kwargs)

            #logger.debug(['_cach_key.......',_cache_key])
            result = cache.get(_cache_key)

            if not result:
                result = fn(*args, **kwargs)
                cache.set(_cache_key, result, time)

            return result
        return wrapper
    return decorator
#-------------------------------------------------------------#

def get_index(bookname):
    res = index_cache.get(bookname)
    if res:
        return res
    return None


def set_index(bookname, instance):
    index_cache[bookname] = instance


def reset_texts_cache():
    """
    Resets caches that only update when text index information changes.
    """
    import sefaria.model as model
    global index_cache
    index_cache = {}
    keys = [
        'toc_cache',
        'toc_json_cache',
        'texts_titles_json',
        'texts_titles_json_he',
        'all_titles_regex_en',
        'all_titles_regex_he',
        'all_titles_regex_en_commentary',
        'all_titles_regex_he_commentary',
        'all_titles_regex_en_terms',
        'all_titles_regex_he_terms',
        'all_titles_regex_en_commentary_terms',
        'all_titles_regex_he_commentary_terms',
        'full_title_list_en',
        'full_title_list_he',
        'full_title_list_en_commentary',
        'full_title_list_he_commentary',
        'full_title_list_en_commentators',
        'full_title_list_he_commentators',
        'full_title_list_en_commentators_commentary',
        'full_title_list_he_commentators_commentary',
        'full_title_list_en_terms',
        'full_title_list_he_terms',
        'full_title_list_en_commentary_terms',
        'full_title_list_he_commentary_terms',
        'full_title_list_en_commentators_terms',
        'full_title_list_he_commentators_terms',
        'full_title_list_en_commentators_commentary_terms',
        'full_title_list_he_commentators_commentary_terms',
        'title_node_dict_en',
        'title_node_dict_he',
        'title_node_dict_en_commentary',
        'title_node_dict_he_commentary',
        'term_dict_en',
        'term_dict_he'
    ]
    for key in keys:
        delete_cache_elem(key)

    delete_template_cache('texts_list')
    delete_template_cache('leaderboards')
    model.Ref.clear_cache()
    model.library.local_cache = {}
    cache.clear()


def process_index_change_in_cache(indx, **kwargs):
    """_args = ('make_toc_html', kwargs["old"])
    kw_args = {'zoom': 1}
    key = cache_get_key(_args, kw_args)
    delete_cache_elem(key)"""
    reset_texts_cache()
    if USE_VARNISH:
        from sefaria.system.sf_varnish import invalidate_index
        invalidate_index(indx)

def process_index_delete_in_cache(indx, **kwargs):
    reset_texts_cache()
    if USE_VARNISH:
        from sefaria.system.sf_varnish import invalidate_index, invalidate_counts
        invalidate_index(indx.title)
        invalidate_counts(indx.title)

def process_new_commentary_version_in_cache(ver, **kwargs):
    if " on " in ver.title:
        reset_texts_cache()

def get_cache_elem(key):
    return cache.get(key)


def set_cache_elem(key, value, duration = 600000):
    return cache.set(key, value, duration)


def delete_cache_elem(key):
    return cache.delete(key)


def get_template_cache(fragment_name='', *args):
    cache_key = 'template.cache.%s.%s' % (fragment_name, hashlib.md5(u':'.join([arg for arg in args])).hexdigest())
    print cache_key
    return get_cache_elem(cache_key)


def delete_template_cache(fragment_name='', *args):
    delete_cache_elem('template.cache.%s.%s' % (fragment_name, hashlib.md5(u':'.join([arg for arg in args])).hexdigest()))

