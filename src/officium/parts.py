import itertools
import re

import jinja2

from officium import data
from officium.psalmish import descriptor_to_psalmish, PsalmishWithGloria

class Group:
    child_default = itertools.cycle([str])
    _title = None

    def __init__(self, contents, **meta):
        self.contents = contents
        self.meta = meta

    def resolve(self):
        for content in self.contents:
            yield content

    @classmethod
    def transform(cls, contents, lang_data):
        return contents

    @property
    def title(self):
        pass

    @property
    def scripture_ref(self):
        return self.meta.get('scripture_ref')


class SingleAlleluiaMixin:
    @classmethod
    def ensure_alleluia(cls, text, lang_data):
        # XXX: The reachings into lang_data should be encapsulated away
        # somewhere, and the compiled result cached, too.
        pattern = re.compile(r'\W*' + lang_data['formula-alleluia-simplicis'] +
                             r'\W*$')
        if not re.search(pattern, text):
            text = re.sub(r'\W*$', lang_data['alleluia-simplex'][0], text,
                          count=1)
        return text

    @classmethod
    def transform(cls, contents, lang_data):
        # Transform the final element to ensure that it ends with "alleluia".
        contents = list(contents)
        indices = [i for (i, x) in enumerate(contents) if isinstance(x, str)]
        if indices:
            contents[indices[-1]] = cls.ensure_alleluia(contents[indices[-1]],
                                                        lang_data)
        return contents

class Antiphon(Group): pass
class AntiphonWithAlleluia(SingleAlleluiaMixin, Antiphon): pass
class PsalmVerse(Group): pass
class Chapter(Group): pass
class HymnLine(Group): pass
class HymnVerse(Group):
    child_default = itertools.cycle([HymnLine])
class Hymn(Group):
    child_default = itertools.cycle([HymnVerse])
    title = 'hymnus'
class Versicle(Group): pass
class VersicleWithAlleluia(SingleAlleluiaMixin, Versicle): pass
class VersicleResponse(Group): pass
class VersicleResponseWithAlleluia(SingleAlleluiaMixin, VersicleResponse): pass
class VersicleWithResponse(Group):
    child_default = itertools.cycle([Versicle, VersicleResponse])
class VersicleWithResponseWithAlleluia(Group):
    child_default = [VersicleWithAlleluia, VersicleResponseWithAlleluia]
class Oration(Group): pass
class OrationConclusion(Group): pass


class TemplateContextLookup:
    def __init__(self, symbols, lang_data):
        self.symbols = symbols
        self.lang_data = lang_data

    def __getattr__(self, attr):
        # XXX: Fail nicely here if attr is not in symbols.
        key = self.symbols[attr]
        # XXX: Should some of this use the index??
        return self.lang_data.get(self.lang_data.lookup([key]), '?')


class TemplateContext:
    def __init__(self, direct_symbols, indirect_symbols,
                 indirect_label='officium'):
        self.direct_symbols = direct_symbols
        self.indirect_symbols = indirect_symbols
        self.indirect_label = indirect_label

    def expand(self, value, lang_data):
        template = jinja2.Template(value)
        lookup = TemplateContextLookup(self.indirect_symbols, lang_data)
        return template.render(
            {self.indirect_label: lookup},
            **self.direct_symbols
        )


class StructuredLookup:
    # Classes that can be referred to by a label.
    labelled_classes = {
    }

    def __init__(self, path, default_class=Group, template_context=None,
                 list_root=False, raw_filter=None):
        self.path = path
        self.default_class = default_class
        if template_context is None:
            template_context = TemplateContext({}, {})
        self.template_context = template_context
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
            return self.build_renderable_list(classes, child, lang_data)
        else:
            return [self.build_renderable(self.default_class, child, lang_data)]

    def build_renderable(self, default_class, raw, lang_data):
        record_class, value, meta = data.maybe_labelled(raw,
                                                        self.labelled_classes,
                                                        default_class)

        # XXX: record_class and record_arg are bad names.

        if issubclass(record_class, Group):
            # We're creating a Group, so we iterate to provide child-defaults.
            children = self.build_renderable_list(record_class.child_default,
                                                  value, lang_data)
            children = record_class.transform(children, lang_data)
            return record_class(children, **meta)
        else:
            # We're not a Group.  Lists are not allowed.
            if isinstance(value, list):
                raise DataValidationError("List in non-Group context %r: %r" %
                                          (record_class, raw))
            if meta:
                raise DataValidationError("Meta in non-Group context %r: %r" %
                                          (record_class, raw))

            value = self.template_context.expand(value, lang_data)
            return record_class(value)

        assert False, "Unreachable"

    def build_renderable_list(self, default_classes, raw, lang_data):
        if not isinstance(raw, list):
            raw = [raw]
        return [self.build_renderable(default_class, item, lang_data)
                for (item, default_class) in zip(raw, default_classes)]


class PsalmishWithAntiphon:
    def __init__(self, antiphon, psalmishes, template_context):
        self.antiphon = antiphon
        self.psalmishes = psalmishes
        self.template_context = template_context

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
            yield StructuredLookup(key, PsalmVerse, self.template_context,
                                   list_root=True, raw_filter=the_filter)
            if psalmish.conclusion:
                yield StructuredLookup(psalmish.conclusion, PsalmVerse,
                                       self.template_context, list_root=True)
        yield self.antiphon


class Psalmody:
    def __init__(self, antiphons_path, psalms, template_context,
                 antiphon_class=Antiphon,
                 default_psalm_class=PsalmishWithGloria):
        self.antiphons_path = antiphons_path
        self.psalms = psalms
        self.template_context = template_context
        self.antiphon_class = antiphon_class
        self.default_psalm_class = default_psalm_class

    def resolve(self, lang_data):
        lookup = StructuredLookup(self.antiphons_path, self.antiphon_class,
                                  self.template_context, list_root=True)
        antiphons = lookup.resolve(lang_data)

        # Special case: If we have only one antiphon but multiple psalm-sets,
        # flatten the psalm-sets into a single psalm-set.
        if len(antiphons) == 1 and len(self.psalms) > 1:
            self.psalms = [
                [psalm for psalms in self.psalms for psalm in psalms]
            ]

        return [Group(
            PsalmishWithAntiphon(
                antiphon,
                [descriptor_to_psalmish(psalm, self.default_psalm_class)
                 for psalm in psalms],
                self.template_context,
            )
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
