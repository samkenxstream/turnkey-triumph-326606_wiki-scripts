#! /usr/bin/env python3

import datetime
import itertools
import bisect

def parse_date(date):
    """
    Converts `ISO 8601`_ dates generated by the MediaWiki API into
    :py:class:`datetime.datetime` objects.

    This will return a time in what the wiki thinks is UTC. Plan
    accordingly for bad server configurations.

    .. _`ISO 8601`: http://en.wikipedia.org/wiki/ISO_8601

    :param date: string ISO 8601 date representation
    :returns: :py:class:`datetime.datetime` object
    """
    # MediaWiki API dates are always of the format
    #   YYYY-MM-DDTHH:MM:SSZ
    # (see $formats in wfTimestamp() in includes/GlobalFunctions.php)

    # strptime is slooow!
    #return datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ')
    return datetime.datetime(int(date[:4]), int(date[5:7]), int(date[8:10]),
            int(date[11:13]), int(date[14:16]), int(date[17:19]))

# test if given string is ASCII
def is_ascii(text):
    try:
        text.encode("ascii")
        return True
    except:
        return False

# split ``list_`` into chunks of fixed length ``bs``
def list_chunks(list_, bs):
    return (list_[i:i+bs] for i in range(0, len(list_), bs))

# yield from ``iterable`` by chunks of fixed length ``bs``
# adjusted from http://stackoverflow.com/questions/24527006/split-a-generator-into-chunks-without-pre-walking-it/24527424#24527424
def iter_chunks(iterable, bs):
    iterator = iter(iterable)
    for first in iterator:
        yield itertools.chain([first], itertools.islice(iterator, bs - 1))

class ListOfDictsAttrWrapper(object):
    """ A list-like wrapper around list of dicts, operating on a given attribute.
    """
    def __init__(self, dict_list, attr):
        self.dict_list = dict_list
        self.attr = attr

    def __getitem__(self, index):
        return self.dict_list[index][self.attr]

    def __len__(self):
        return self.dict_list.__len__()

def bisect_find(data_list, key, index_list=None):
    """
    Find an element in a sorted list using the bisect method.

    :param data_list: list of elements to be returned from
    :param key: element to be found in ``index_list``
    :param index_list: an optional list of indexes where ``key`` is searched for,
                       by default ``data_list`` is taken. Has to be sorted.
    :returns: ``data_list[i]`` if ``index_list[i] == key``
    :raises IndexError: when ``key`` is not found
    """
    index_list = data_list if index_list is None else index_list
    i = bisect.bisect_left(index_list, key)
    if i != len(index_list) and index_list[i] == key:
        return data_list[i]
    raise IndexError

def bisect_insert_or_replace(data_list, key, data_element=None, index_list=None):
    """
    Insert an element into a sorted list using the bisect method. If an element
    is found in the list, it is replaced.

    :param data_list: list of elements to be inserted into
    :param data_element: an element to be inserted. By default ``key`` is taken.
    :param key: a key used for searching
    :param index_list: an optional list of indexes where ``key`` is searched for,
                       by default ``data_list`` is taken. Has to be sorted.
    """
    data_element = key if data_element is None else data_element
    index_list = data_list if index_list is None else index_list
    i = bisect.bisect_left(index_list, key)
    if i != len(index_list) and index_list[i] == key:
        data_list[i] = data_element
    else:
        data_list.insert(i, data_element)

def dmerge(source, destination):
    """
    Deep merging of dictionaries.
    """
    if not isinstance(source, dict) or not isinstance(destination, dict):
        raise TypeError("both 'source' and 'destination' must be of type 'dict'")
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            dmerge(value, node)
        elif isinstance(value, list):
            node = destination.setdefault(key, [])
            node.extend(value)
        else:
            destination[key] = value

    return destination
