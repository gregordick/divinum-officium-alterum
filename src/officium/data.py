class Data:
    def __init__(self, dictionary):
        self.dictionary = dictionary

    def lookup(self, keys):
        for key in keys:
            if key in self.dictionary:
                return key
        # XXX: For bringup, return a string rather than raising.
        return "NOT FOUND: " + key
        raise KeyError(keys)

    def get(self, *args, **kwargs):
        return self.dictionary.get(*args, **kwargs)

    def __getitem__(self, *args, **kwargs):
        return self.dictionary.__getitem__(*args, **kwargs)

    def __contains__(self, *args, **kwargs):
        return self.dictionary.__contains__(*args, **kwargs)
