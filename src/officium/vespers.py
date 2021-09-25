from . import offices
from . import parts
from . import psalmish
from . import util

class Vespers:
    default_psalmish_class = parts.PsalmishWithGloria

    def __init__(self, date, generic_data, index, calendar_resolver, season,
                 season_keys, office, concurring, commemorations):
        self._date = date
        self._generic_data = generic_data
        self._index = index
        self._calendar_resolver = calendar_resolver
        self._season = season
        self._season_keys = season_keys
        self._office = office
        self._is_first = office in concurring

        # Knowing the concurring offices allows us to determine whether a
        # commemoration is for first Vespers.
        self._concurring = concurring

        self._commemorations = list(commemorations)

        # Template context for the office of the day.  TODO: Handle offices
        # that are from the chapter of the following.
        self._primary_template_context = self.make_template_context(self._office)

    def lookup_order(self, office, items):
        # XXX: The use of lambdas here is probably overengineered -- we could
        # just mandate that the paths are prefixes and do a join rather than a
        # call -- and the scoping doesn't behave in the way that we'd like.

        paths = [
            lambda item, key=key: '%s/%s' % (key, item)
            for key in office.keys
        ]
        season = [
            lambda item, key=key: 'proprium/%s/%s' % (key, item)
            for key in self._season_keys
        ]
        # Seasonal keys take precedence over office keys for and only for
        # temporal offices.
        if office.temporal:
            paths = season + paths
        else:
            paths += season
        # Fall back to propers from the preceding Sunday.  XXX: This is wrong,
        # in two respects: firstly, it should be any non-Sunday temporal
        # office, and not necessarily a feria; and secondly, slicing and dicing
        # the first key is in very poor taste.
        if isinstance(office, offices.Feria):
            sunday = office.keys[0][:-1] + '0'
            paths.append(lambda item: 'proprium/%s/%s' % (sunday, item))
        prefixes = []
        if self._season:
            prefixes.append(self._season + '/')
        prefixes.append('')
        for prefix in prefixes:
            paths += [
                lambda item, prefix=prefix: 'psalterium/%s%s/%s' % (prefix,
                                                                    util.day_ids[self._date.day_of_week],
                                                                    item),
                lambda item, prefix=prefix: 'psalterium/%s%s' % (prefix, item),
            ]
        items = list(items)
        for path in paths:
            for item in items:
                yield path(item)

    def lookup(self, office, is_first, *items):
        base = [
            ['ad-i-vesperas' if is_first else 'ad-ii-vesperas'],
            ['ad-vesperas'],
            [],
        ]
        return self._index.lookup(self.lookup_order(
            office, ('/'.join(b + [item]) for item in items for b in base)))

    def lookup_main(self, *items):
        return self.lookup(self._office, self._is_first, *items)

    def psalmody(self, antiphon_class=parts.Antiphon):
        antiphons = self.lookup_main('antiphonae')
        psalms = self.lookup_main('psalmi')
        yield parts.Psalmody(antiphons, self._generic_data[psalms],
                             self._primary_template_context, antiphon_class,
                             self.default_psalmish_class)

    def versicle_and_response(self, vr_class=parts.VersicleWithResponse):
        versicle_pair = self.lookup_main('versiculum')
        yield parts.StructuredLookup(versicle_pair, vr_class,
                                     self._primary_template_context)

    def chapter_hymn_and_verse(self, vr_class):
        yield parts.StructuredLookup(self.lookup_main('capitulum'),
                                     parts.Chapter,
                                     self._primary_template_context)
        yield parts.StructuredLookup(self.lookup_main('hymnus'),
                                     parts.Hymn, self._primary_template_context)
        yield from self.versicle_and_response(vr_class)

    def magnificat(self, antiphon_class=parts.Antiphon):
        path = self.lookup_main('ad-magnificat')
        mag_ant = parts.StructuredLookup(path, antiphon_class,
                                         self._primary_template_context)
        # XXX: Slashes.
        mag = self.default_psalmish_class('ad-vesperas/magnificat')
        yield parts.PsalmishWithAntiphon(mag_ant, [mag],
                                         self._primary_template_context)

    def pater(self):
        yield parts.StructuredLookup('orationes/pater-noster-secreto',
                                     template_context=self._primary_template_context)
        yield parts.StructuredLookup('orationes/et-ne-nos-inducas',
                                     parts.VersicleWithResponse,
                                     self._primary_template_context)

    def preces(self):
        yield from self.pater()
        yield parts.StructuredLookup('officium-defunctorum/preces',
                                     parts.VersicleWithResponse,
                                     self._primary_template_context)
        # XXX: Elide when necessary.
        yield parts.StructuredLookup('versiculi/domine-exaudi',
                                     parts.VersicleWithResponse,
                                     self._primary_template_context)

    def oration(self):
        oration_path = self.lookup_main('oratio-super-populum', 'oratio')
        oration = parts.StructuredLookup(oration_path, parts.Oration,
                                         self._primary_template_context)
        yield parts.Group([
            parts.dominus_vobiscum(),
            parts.oremus(),
            oration,
            parts.oration_conclusion(oration_path, self._generic_data),
            parts.amen(),
        ])

    def commemorations(self, antiphon_class, vr_class):
        for i, commem in enumerate(self._commemorations):
            is_first = commem in self._concurring
            versicle_pair = self.lookup(commem, is_first, 'versiculum')
            oration_path = self.lookup(commem, is_first,
                                       'oratio-super-populum', 'oratio')
            template_context = self.make_template_context(commem)
            part_list = [
                parts.StructuredLookup(self.lookup(commem, is_first,
                                                   'ad-magnificat'),
                                       antiphon_class, template_context),
                parts.StructuredLookup(versicle_pair, vr_class,
                                       template_context),
                parts.oremus(),
                parts.StructuredLookup(oration_path, parts.Oration,
                                       template_context),
            ]
            # Only the last commemoration gets the conclusion.
            if i == len(self._commemorations) - 1:
                part_list += [
                    parts.oration_conclusion(oration_path, self._generic_data),
                    parts.amen(),
                ]
            yield parts.Group(part_list)

    def conclusion(self):
        yield parts.Group([
            parts.dominus_vobiscum(),
            parts.VersicleWithResponse([
                parts.StructuredLookup('versiculi/benedicamus-domino',
                                       parts.Versicle),
                parts.StructuredLookup('versiculi/deo-gratias',
                                       parts.VersicleResponse),
            ]),
            parts.VersicleWithResponse([
                parts.StructuredLookup('versiculi/fidelium-animae',
                                       parts.Versicle),
                parts.StructuredLookup('versiculi/amen',
                                       parts.VersicleResponse),
            ]),
        ])

    def resolve(self):
        # XXX: Information about the season should come with the offices for the
        # day.  Also, take care about the boundaries.
        easter = self._calendar_resolver.easter_sunday(self._date.year)
        alleluia = not (easter - 7 * 9 <= self._date < easter - 1)
        eastertide = easter <= self._date < easter + 8 * 7 - 1

        if eastertide:
            antiphon_class = parts.AntiphonWithAlleluia
            vr_class = parts.VersicleWithResponseWithAlleluia
        else:
            antiphon_class = parts.Antiphon
            vr_class = parts.VersicleWithResponse

        yield parts.deus_in_adjutorium(alleluia)

        yield from self.psalmody(antiphon_class)
        yield from self.chapter_hymn_and_verse(vr_class)
        yield from self.magnificat(antiphon_class)
        yield from self.oration()
        yield from self.commemorations(antiphon_class, vr_class)
        yield from self.conclusion()

    @staticmethod
    def make_template_context(office):
        # XXX: Using keys[0] is wrong; factor out multi-key lookup so that
        # TemplateContext can use it too.
        return parts.TemplateContext(
            direct_symbols={},
            indirect_symbols={
                'nomen_' + case: '/nomen/'.join([office.keys[0], case])
                for case in [
                    'nominativo',
                    'vocativo',
                    'accusativo',
                    'genitivo',
                    'dativo',
                    'ablativo',
                ]
            },
        )


class HolySaturdayVespers(Vespers):
    def resolve(self):
        yield from self.psalmody(parts.AntiphonWithAlleluia)
        yield from self.magnificat(parts.AntiphonWithAlleluia)
        yield from self.oration()
        yield from self.conclusion()


class EasterOctaveVespers(Vespers):
    def chapter_hymn_and_verse(self, vr_class):
        yield parts.StructuredLookup(self.lookup_main('haec-dies'),
                                     parts.Antiphon,
                                     self._primary_template_context)


class VespersOfTheDead(Vespers):
    default_psalmish_class = psalmish.PsalmishWithRequiem

    def resolve(self):
        yield from self.psalmody()
        yield from self.versicle_and_response()
        yield from self.magnificat()
        yield from self.preces()
        yield from self.oration()
        yield from self.conclusion()

    def conclusion(self):
        yield parts.Group([
            parts.StructuredLookup('versiculi/requiem',
                                   parts.VersicleWithResponse),
            parts.StructuredLookup('versiculi/requiescant',
                                   parts.VersicleWithResponse),
        ])


class TriduumVespers(Vespers):
    default_psalmish_class = psalmish.PsalmishWithoutGloria

    def resolve(self):
        yield from self.psalmody()
        yield from self.magnificat()
        yield from self.christus_factus_est()
        yield from self.miserere()
        yield from self.oration()

    def christus_factus_est(self):
        yield parts.StructuredLookup(self.lookup_main('christus-factus-est'),
                                     parts.Antiphon,
                                     self._primary_template_context)

    def miserere(self):
        yield parts.StructuredLookup('psalterium/psalmi/50', parts.PsalmVerse,
                                     self._primary_template_context,
                                     list_root=True)

    def oration(self):
        oration_path = self.lookup_main('oratio')
        oration = parts.StructuredLookup(oration_path, parts.Oration,
                                         self._primary_template_context)
        yield parts.Group([
            oration,
            parts.oration_conclusion(oration_path, self._generic_data),
            parts.amen(),
        ])
