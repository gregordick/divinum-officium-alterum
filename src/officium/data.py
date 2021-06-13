class DataValidationError(Exception):
    pass


class Data:
    def __init__(self, dictionary):
        self.dictionary = dictionary.copy()
        self.redirections = {}

    def lookup(self, keys):
        first = None # XXX: See below
        for key in keys:
            if first is None:
                first = key
            for real_key in self.gen_redirections(key):
                if real_key in self.dictionary:
                    return real_key
        # XXX: For bringup, return a string rather than raising.
        return "NOT FOUND: " + first
        raise KeyError(keys)

    def get(self, *args, **kwargs):
        return self.dictionary.get(*args, **kwargs)

    def __getitem__(self, *args, **kwargs):
        return self.dictionary.__getitem__(*args, **kwargs)

    def __contains__(self, *args, **kwargs):
        return self.dictionary.__contains__(*args, **kwargs)

    def create(self, d):
        for key in d:
            self.dictionary[key] = d[key]

    def append(self, d):
        for key in d:
            entries = self.dictionary.setdefault(key, [])
            entries += d[key]

    def redirect(self, redirection_dict):
        for (redirect_name, target) in redirection_dict.items():
            assert redirect_name not in self.redirections
            self.redirections[redirect_name] = target

    def gen_redirections(self, key):
        # TODO: Check for cycles.

        # First, try with no redirections at all.
        yield key
        components = key.split('/')
        # Then try all possible redirections, starting with the longest.
        for prefix_len in range(len(components), 0, -1):
            prefix = '/'.join(components[0:prefix_len])
            if prefix in self.redirections:
                redirected_path = '/'.join([self.redirections[prefix]] +
                                           components[prefix_len:])
                yield from self.gen_redirections(redirected_path)


def maybe_labelled(raw, labels, default_class):
    meta = {}
    cls = default_class
    if isinstance(raw, dict):
        try:
            meta = dict(raw)
            value = meta.pop('content')
        except KeyError:
            raise DataValidationError("No content: %r" % (raw,))
        if 'type' in meta:
            try:
                key = meta.pop('type')
                cls = labels[key]
            except KeyError:
                raise DataValidationError("Unrecognised type: %s" % (key,))
    else:
        # Not a dictionary.
        value = raw
    return cls, value, meta
