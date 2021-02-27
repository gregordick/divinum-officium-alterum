import itertools


class Group:
    child_default = itertools.cycle([str])

    def __init__(self, contents):
        self.contents = contents

    def resolve(self):
        for content in self.contents:
            yield content


class Antiphon(Group): pass
class PsalmVerse(Group): pass
class Chapter(Group): pass
class Hymn(Group): pass
class Versicle(Group): pass
class VersicleResponse(Group): pass
class VersicleWithResponse(Group):
    child_default = [Versicle, VersicleResponse]
class Oration(Group): pass


class DataValidationError(Exception):
    pass


class StructuredLookup:
    # Classes that can be referred to by a label.
    labelled_classes = {
    }

    def __init__(self, path, default_class=str, list_root=False):
        self.path = path
        self.default_class = default_class
        self.list_root = list_root

    def __repr__(self):
        return '%s(%s, %s)' % (self.__class__.__name__, self.path,
                               self.default_class.__name__)

    def resolve(self, lang_data):
        # XXX: Silently handle missing things by returning the raw path.
        child = lang_data.get(self.path, self.path)
        if self.list_root:
            classes = itertools.cycle([self.default_class])
            return self.build_renderable_list(classes, child)
        else:
            return [self.build_renderable(self.default_class, child)]

    @classmethod
    def build_renderable(cls, default_class, raw):
        try:
            [(key, value)] = raw.items()
            try:
                record_class = cls.labelled_classes[key]
            except KeyError:
                raise DataValidationError("Unrecognised type: %s" % (key,))
        except ValueError:
            # Too many/few keys.
            raise DataValidationError("Must have exactly one key: %r" % (raw,))
        except AttributeError:
            # Not a dictionary.
            record_class = default_class
            value = raw

        # XXX: record_class and record_arg are bad names.

        if issubclass(record_class, Group):
            # We're creating a Group, so we iterate to provide child-defaults.
            record_arg = cls.build_renderable_list(record_class.child_default,
                                                   value)
        else:
            record_arg = value

            # We're not a Group.  Lists are not allowed.
            if isinstance(value, list):
                raise DataValidationError("List in non-Group context %r: %r" %
                                          (record_class, raw))

        return record_class(record_arg)

    @classmethod
    def build_renderable_list(cls, default_classes, raw):
        if not isinstance(raw, list):
            raw = [raw]
        return [cls.build_renderable(default_class, item)
                for (item, default_class) in zip(raw, default_classes)]


class PsalmishWithAntiphon:
    def __init__(self, antiphon, psalmishes):
        self.antiphon = antiphon
        self.psalmishes = psalmishes

    def resolve(self):
        # XXX: Proper classes, Gloria.
        yield self.antiphon
        for psalmish in self.psalmishes:
            yield StructuredLookup(psalmish, PsalmVerse)
        yield self.antiphon


class Psalmody:
    def __init__(self, antiphons_path, psalms):
        self.antiphons_path = antiphons_path
        self.psalms = psalms

    def resolve(self, lang_data):
        lookup = StructuredLookup(self.antiphons_path, Antiphon, list_root=True)
        antiphons = lookup.resolve(lang_data)
        return [Group(
            PsalmishWithAntiphon(antiphon, psalms)
            for (antiphon, psalms) in zip(antiphons, self.psalms)
        )]


def deus_in_adjutorium(alleluia):
    def generator():
        yield VersicleWithResponse([
            StructuredLookup('versiculi/deus-in-adjutorium', Versicle),
            StructuredLookup('versiculi/domine-ad-adjuvandum',
                             VersicleResponse),
        ])
        yield StructuredLookup('versiculi/gloria-patri')
        yield StructuredLookup('versiculi/sicut-erat')
        yield StructuredLookup('versiculi/alleluja' if alleluia else
                               'versiculi/laus-tibi-domine')
    return Group(generator())


def dominus_vobiscum():
    def generator():
        yield StructuredLookup('versiculi/dominus-vobiscum',
                               VersicleWithResponse)
    return VersicleWithResponse(generator())
