from itertools import islice


def chunked(it, size):
    it = iter(it)
    return iter(lambda: tuple(islice(it, size)), ())
