import itertools
import re

from officium import data
from officium.psalmish import descriptor_to_psalmish

class Group:
    child_default = itertools.cycle([str])
    _title = None

    def __init__(self, contents, **meta):
        self.contents = contents
        self.meta = meta

    def resolve(self):
        for content in self.contents:
            yield content

    @property
    def title(self):
        pass

    @property
    def scripture_ref(self):
        return self.meta.get('scripture_ref')


class Antiphon(Group): pass
class PsalmVerse(Group): pass
class Chapter(Group): pass
class HymnLine(Group): pass
class HymnVerse(Group):
    child_default = itertools.cycle([HymnLine])
class Hymn(Group):
    child_default = itertools.cycle([HymnVerse])
    title = 'hymnus'
class Versicle(Group): pass
class VersicleResponse(Group): pass
class VersicleWithResponse(Group):
    child_default = [Versicle, VersicleResponse]
class Oration(Group): pass
class OrationConclusion(Group): pass


class StructuredLookup:
    # Classes that can be referred to by a label.
    labelled_classes = {
    }

    def __init__(self, path, default_class=Group, list_root=False,
                 raw_filter=None):
        self.path = path
        self.default_class = default_class
        self.list_root = list_root
        self.raw_filter = raw_filter

    def __repr__(self):
        return '%s(%s, %s)' % (self.__class__.__name__, self.path,
                               self.default_class.__name__)

    def lookup_raw(self, lang_data):
        raw = lang_data.get(self.path, self.path)
        if self.raw_filter:
            raw = self.raw_filter(raw)
        return raw

    def resolve(self, lang_data):
        # XXX: Silently handle missing things by returning the raw path.
        child = self.lookup_raw(lang_data)
        if self.list_root:
            classes = itertools.cycle([self.default_class])
            return self.build_renderable_list(classes, child)
        else:
            return [self.build_renderable(self.default_class, child)]

    @classmethod
    def build_renderable(cls, default_class, raw):
        record_class, value, meta = data.maybe_labelled(raw,
                                                        cls.labelled_classes,
                                                        default_class)

        # XXX: record_class and record_arg are bad names.

        if issubclass(record_class, Group):
            # We're creating a Group, so we iterate to provide child-defaults.
            children = cls.build_renderable_list(record_class.child_default,
                                                 value)
            return record_class(children, **meta)
        else:
            # We're not a Group.  Lists are not allowed.
            if isinstance(value, list):
                raise DataValidationError("List in non-Group context %r: %r" %
                                          (record_class, raw))
            if meta:
                raise DataValidationError("Meta in non-Group context %r: %r" %
                                          (record_class, raw))

            return record_class(value)

        assert False, "Unreachable"

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

    @staticmethod
    def make_psalm_verse_filter(start, end):
        def the_filter(raw_verses):
            def gen():
                for verse in raw_verses:
                    # XXX: The verse-numbering should be specified in a more
                    # structured way, rather than in line with the text.
                    m = re.match(r'\d+:(\d+)', verse)
                    if not m:
                        # XXX: Shouldn't happen, but we can't guarantee this
                        # yet.
                        yield verse
                    else:
                        verse_num = int(m.group(1))
                        if start <= verse_num <= end:
                            yield verse
            # XXX: It would be nice not to have to collapse the generator here.
            return list(gen())
        return the_filter

    def resolve(self):
        # XXX: Proper classes, Gloria.
        yield self.antiphon
        for psalmish in self.psalmishes:
            # XXX: This is a DO-style partial-psalm spec.
            m = re.match(r'(.*)[(](\d+)-(\d+)[)]', psalmish.key)
            if m:
                key, start, end = m.groups()
                the_filter = self.make_psalm_verse_filter(int(start), int(end))
            else:
                key = psalmish.key
                the_filter = None
            yield StructuredLookup(key, PsalmVerse, list_root=True,
                                   raw_filter=the_filter)
            if psalmish.gloria:
                yield StructuredLookup('versiculi/gloria-patri-post-psalmum',
                                       PsalmVerse, list_root=True)
        yield self.antiphon


class Psalmody:
    def __init__(self, antiphons_path, psalms):
        self.antiphons_path = antiphons_path
        self.psalms = psalms

    def resolve(self, lang_data):
        lookup = StructuredLookup(self.antiphons_path, Antiphon, list_root=True)
        antiphons = lookup.resolve(lang_data)
        return [Group(
            PsalmishWithAntiphon(antiphon, [descriptor_to_psalmish(psalm)
                                            for psalm in psalms])
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
    return StructuredLookup('versiculi/dominus-vobiscum', VersicleWithResponse)


def oremus():
    return StructuredLookup('versiculi/oremus')


def amen():
    return StructuredLookup('versiculi/amen', VersicleResponse)


def oration_conclusion(oration_path, generic_data):
    conclusion_base = generic_data['conclusions'].get(oration_path,
                                                      'per-dominum')
    return StructuredLookup(conclusion_base, OrationConclusion)
