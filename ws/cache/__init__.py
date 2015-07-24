#! /usr/bin/env python3

# TODO:
#   compression level should be configurable, as well as compression format (e.g. optional dependency on python-lz4)
#   improve definition of meta data keys with respect to (de)serialization
#   implement some database versioning: either epoch, version number or timestamp of the database initialization

import os
import gzip
import json
import hashlib
import datetime

def md5sum(bytes_):
    h = hashlib.md5()
    h.update(bytes_)
    return h.hexdigest()

class CacheDb:
    """
    Base class for caching databases. The database is saved on disk in the
    gzipped JSON format. The data is represented by the ``self.data`` structure,
    whose type depends on the implementation in each subclass (generally a
    ``list`` or ``dict``). There is also a ``self.meta`` structure keeping the
    meta data such as timestamp of the last update.

    The data elements can be accessed using the subscript syntax ``db["key"]``,
    which triggers a lazy update/initialization of the database. The meta data
    can be accessed as attributes (e.g. ``db.attribute``), which does not
    trigger an update.

    :param api: an :py:class:`MediaWiki.API` instance
    :param dbname: a name of the database (``str``), usually the name of the
                   subclass
    :param autocommit: whether to automatically call :py:meth:`self.dump()`
                       after each update of the database
    """

    meta = {}
    data = None

    # format for JSON (de)serialization of datetime.datetime timestamps
    ts_format = "%Y-%m-%dT%H:%M:%S.%f"

    def __init__(self, api, dbname, autocommit=True):
        self.api = api
        self.dbname = dbname
        self.autocommit = autocommit

        cache_dir = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
        dbdir = os.path.join(cache_dir, "wiki-scripts", self.api.get_hostname())
        self.dbpath = os.path.join(dbdir, self.dbname + ".db.json.gz")
        self.metapath = os.path.join(dbdir, self.dbname + ".meta")

    def load(self, key=None):
        """
        Try to load data from disk. When data on disk does not exist yet, calls
        :py:meth:`self.init()` to initialize the database and :py:meth:`self.dump()`
        immediately after to save the initial state to disk.

        Called automatically from :py:meth:`self.__init__()`, it is not necessary to call it manually.

        :param key: passed to :py:meth:`self.init()`, necessary for proper lazy
                    initialization in case of multi-key database
        """
        if os.path.isfile(self.dbpath):
            print("Loading data from {} ...".format(self.dbpath))
            db = gzip.open(self.dbpath, mode="rb")
            s = db.read()
            md5_new = md5sum(s)

            # TODO: make meta file mandatory at some point
            if os.path.isfile(self.metapath):
                meta = open(self.metapath, mode="rt", encoding="utf-8")
                self.meta.update(json.loads(meta.read()))

                # parse timestamp
                if "timestamp" in self.meta:
                    self.meta["timestamp"] = datetime.datetime.strptime(self.meta["timestamp"], self.ts_format)

                if md5_new != self.md5:
                    raise CacheDbError("md5sums of the database {} differ. Please investigate...".format(self.dbpath))
            else:
                self.meta["md5"] = md5_new

            self.data = json.loads(s.decode("utf-8"))
        else:
            self.init(key)

    def dump(self):
        """
        Save data to disk. When :py:attribute:`self.autocommit` is ``True``, it is
        called automatically from :py:meth:`self.init()` and :py:meth:`self.update()`.

        After manual modification of the ``self.data`` structure it is necessary to
        call it manually if the change is to be persistent.
        """
        print("Saving data to {} ...".format(self.dbpath))

        # create leading directories
        try:
            os.makedirs(os.path.split(self.dbpath)[0])
        except OSError as e:
            if e.errno != 17:
                raise e

        # update hashes
        s = json.dumps(self.data).encode("utf-8")
        self.meta["md5"] = md5sum(s)

        # create copy and serialize timestamp (the type of the "real" timestamp
        # in self.meta should always be datetime.datetime)
        m = self.meta.copy()
        if "timestamp" in m:
            m["timestamp"] = m["timestamp"].strftime(self.ts_format)

        db = gzip.open(self.dbpath, mode="wb", compresslevel=3)
        db.write(s)
        meta = open(self.metapath, mode="wt", encoding="utf-8")
        meta.write(json.dumps(m, indent=4, sort_keys=True))

    def init(self, key=None):
        """
        Called by :py:meth:`self.load()` when data does not exist on disk yet.
        Responsible for:
          - initializing ``self.data`` structure and performing the initial API
            query,
          - calling :py:meth:`self.dump()` after the query depending on the
            value of :py:attribute:`self.autocommit`,
          - updating ``self.meta["timestamp"]``, either manually or via
            :py:meth:`self._update_timestamp`.

        Has to be defined in subclasses.

        :param key: database key determining which part of the database should be
                    initialized. Can be ignored in case of single-key databases.
        """
        raise NotImplementedError

    def update(self, key=None):
        """
        Called from accessors like :py:meth:`self.__getitem__()` a cache update.
        Responsible for:
          - performing an API query to update the cached data,
          - calling :py:meth:`self.dump()` after the query depending on the
            value of :py:attribute:`self.autocommit`,
          - updating ``self.meta["timestamp"]``, either manually or via
            :py:meth:`self._update_timestamp`.

        Has to be defined in subclasses.

        :param key: database key determining which part of the database should be
                    initialized. Can be ignored in case of single-key databases.
        """
        raise NotImplementedError


    def _update_timestamp(self):
        self.meta["timestamp"] = datetime.datetime.utcnow()

    # TODO: make some decorator to actually run the code only every minute or so
    #       ...or maybe not necessary. The accessed data is mutable anyway, so
    #       the accessors are not actually called very often -- at least for dict.
    def _load_and_update(self, key=None):
        """
        Helper method called from the accessors.
        """
        if self.data is None:
            self.load(key)
        self.update(key)

    def __getitem__(self, key):
        self._load_and_update(key)
        return self.data.__getitem__(key)

    def __iter__(self):
        self._load_and_update()
        return self.data.__iter__()

    def __reversed__(self):
        self._load_and_update()
        return self.data.__reversed__()

    def __contains__(self, item):
        self._load_and_update(item)
        return self.data.__contains__(item)

    def __len__(self):
        return self.data.__len__()


    def __getattr__(self, name):
        """
        Access a meta data element.

        :returns: ``self.meta[name]`` if available, otherwise ``None``
        """
        return self.meta.get(name)


class CacheDbError(Exception):
    """ Raised on database errors, e.g. when loading from disk failed.
    """
    pass


from .AllRevisionsProps import *
from .AllUsersProps import *
from .LatestRevisionsText import *

__all__ = ["CacheDb", "CacheDbError", "AllRevisionsProps", "AllUsersProps", "LatestRevisionsText"]