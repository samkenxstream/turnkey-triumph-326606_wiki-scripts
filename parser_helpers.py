#! /usr/bin/env python3

# TODO: write unit tests

def canonicalize(title):
    """
    Return a canonical form of the title, that is with underscores replaced with
    spaces, leading and trailing whitespace stripped and first letter
    capitalized.

    :param title: a `str` or `mwparserfromhell.nodes.wikicode.Wikicode` object
    :returns: a `str` object
    """
    title = str(title).replace("_", " ").strip()
    title = title[0].upper() + title[1:]
    return title

def get_adjacent_node(wikicode, node, ignore_whitespace=False):
    """
    Get the node immediately following `node` in `wikicode`.

    :param wikicode: a :py:class:`mwparserfromhell.wikicode.Wikicode` object
    :param node: a :py:class:`mwparserfromhell.nodes.Node` object
    :param ignore_whitespace: When True, the whitespace between `node` and the
            node being returned is ignored, i.e. the returned object is
            guaranteed to not be an all white space text, but it can still be a
            text with leading space.
    :returns: a :py:class:`mwparserfromhell.nodes.Node` object or None if `node`
            is the last object in `wikicode`
    """
    i = wikicode.index(node) + 1
    try:
        n = wikicode.get(i)
        while ignore_whitespace and n.isspace():
            i += 1
            n = wikicode.get(i)
        return n
    except IndexError:
        return None

def get_parent_wikicode(wikicode, node):
    """
    Returns the parent of `node` as a `wikicode` object.
    Raises :exc:`ValueError` if `node` is not a descendant of `wikicode`.
    """
    context, index = wikicode._do_strong_search(node, True)
    return context

def remove_and_squash(wikicode, obj):
    """
    Remove `obj` from `wikicode` and fix whitespace in the place it was removed from.
    """
    parent = get_parent_wikicode(wikicode, obj)
    index = parent.index(obj)
    parent.remove(obj)

    def _get_text(index):
        try:
            return parent.get(index)
        except IndexError:
            return None

    prev = _get_text(index - 1)
    next_ = _get_text(index)

    if prev is None and next_ is not None:
        if next_.startswith(" "):
            parent.replace(next_, next_.lstrip(" "))
        elif next_.startswith("\n"):
            parent.replace(next_, next_.lstrip("\n"))
    elif prev is not None and next_ is None:
        if prev.endswith(" "):
            parent.replace(prev, prev.rstrip(" "))
        elif prev.endswith("\n"):
            parent.replace(prev, prev.rstrip("\n"))
    elif prev is not None and next_ is not None:
        if prev.endswith(" ") and next_.startswith(" "):
            parent.replace(prev, prev.rstrip(" "))
            parent.replace(next_, " " + next_.lstrip(" "))
        elif prev.endswith("\n") and next_.startswith("\n"):
            if not prev[:-1].endswith("\n") and not next_[1:].startswith("\n"):
                # leave one linebreak
                parent.replace(prev, prev.rstrip("\n") + "\n")
            parent.replace(next_, next_.replace("\n", "", 1))
        elif prev.endswith("\n"):
            parent.replace(next_, next_.lstrip(" "))
        elif next_.startswith("\n"):
            parent.replace(prev, prev.rstrip(" "))
