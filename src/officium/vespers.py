from . import offices
from . import parts
from . import psalmish
from . import util

class Vespers:
    default_psalmish_class = parts.PsalmishWithGloria
    preces_key = 'ordinarium/ad-vesperas/preces-feriales'

    def __init__(self, date, generic_data, index, calendar_resolver, season,
                 season_keys, doxology, office, morning_offices, concurring,
                 commemorations):
        self._date = date
        self._generic_data = generic_data
        self._index = index
        self._calendar_resolver = calendar_resolver
        self._season = season
        self._season_keys = season_keys
        self._office = office
        self._is_first = office in concurring

        # These are the offices that were said this morning at Lauds, and not
        # only those that have second Vespers.  We need these in order to
        # detect the case where the ferial preces are to be said at Vespers
        # on account of the morning's preces-inducing office, despite that
        # office having ended.
        self._morning_offices = morning_offices

        # Knowing the concurring offices allows us to determine whether a
        # commemoration is for first Vespers.
        self._concurring = concurring

        self._commemorations = list(commemorations)

        # Template context for the office of the day.  TODO: Handle offices
        # that are from the chapter of the following.
        self._primary_template_context = self.make_template_context(self._office)

        if doxology:
            self._doxology = parts.StructuredLookup(doxology, parts.HymnVerse,
                                                    self._primary_template_context)
        else:
            self._doxology = None

    def lookup_order(self, office, items, use_commons=True):
        paths = []

        for keys in [office.keys] + ([['%s/commune' % (key,)
                                       for key in office.keys]]
                                     if use_commons else []):
            if self._season:
                paths += ['%s/%s' % (key, self._season) for key in keys]
            paths += list(keys)

        season = [
            'proprium/%s' % (key,)
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
            paths.append('proprium/%s' % (sunday,))

        psalter_prefixes = []
        if self._season:
            psalter_prefixes.append('/' + self._season)
        psalter_prefixes.append('')
        for prefix in psalter_prefixes:
            paths += [
                'psalterium%s/%s' % (prefix,
                                     util.day_ids[self._date.day_of_week],),
                'psalterium%s' % (prefix,),
            ]

        items = list(items)
        for path in paths:
            for item in items:
                yield '/'.join([path, item])

    def lookup(self, office, is_first, *items, **kwargs):
        base = [
            ['ad-i-vesperas' if is_first else 'ad-ii-vesperas'],
            ['ad-vesperas'],
            [],
        ]
        return self._index.lookup(
            self.lookup_order(
                office,
                ('/'.join(b + [item]) for item in items for b in base),
                **kwargs
            )
        )

    def lookup_main(self, *items, **kwargs):
        return self.lookup(self._office, self._is_first, *items, **kwargs)

    def psalmody(self, antiphon_class=parts.Antiphon):
        use_commons = self._calendar_resolver.uses_common_for_psalmody(self._office)
        antiphons = self.lookup_main('antiphonae', use_commons=use_commons)
        psalms = self.lookup_main('psalmi', use_commons=use_commons)
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
        if self._doxology is not None:
            mutable_hymn_cls = parts.HymnWithProperDoxology(self._doxology)
        else:
            mutable_hymn_cls = parts.Hymn
        # XXX: Factor this out so that it can be used anywhere we might need to
        # look up a hymn.
        yield parts.StructuredLookup(self.lookup_main('hymnus'), parts.Hymn,
                                     self._primary_template_context,
                                     labelled_classes={
                                         'hymnus-cum-doxologia-mutabile':
                                             mutable_hymn_cls,
                                     })
        yield from self.versicle_and_response(vr_class)

    def magnificat(self, antiphon_class=parts.Antiphon):
        path = self.lookup_main('ad-canticum')
        mag_ant = parts.StructuredLookup(path, antiphon_class,
                                         self._primary_template_context)
        # XXX: Slashes.
        mag = self.default_psalmish_class('ad-vesperas/magnificat')
        yield parts.PsalmishWithAntiphon(mag_ant, [mag],
                                         self._primary_template_context)

    def have_ferial_preces(self):
        # The preces should be said if they were said at Lauds and Vespers are
        # not of the following.
        return all([
            self._calendar_resolver.has_ferial_preces(self._morning_offices[0],
                                                      self._date),
            not self._is_first,
        ])

    def kyrie(self):
        yield parts.StructuredLookup('ordinarium/kyrie-simplex',
                                     template_context=self._primary_template_context)

    def pater(self):
        yield parts.StructuredLookup('orationes/pater-noster-secreto',
                                     template_context=self._primary_template_context)
        yield parts.StructuredLookup('orationes/et-ne-nos-inducas',
                                     parts.VersicleWithResponse,
                                     self._primary_template_context)

    def preces(self):
        yield from self.pater()
        yield parts.StructuredLookup(self.preces_key,
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
                                                   'ad-canticum'),
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
        if self.have_ferial_preces():
            yield from self.kyrie()
            yield from self.preces()
        yield from self.oration()
        yield from self.commemorations(antiphon_class, vr_class)
        yield from self.conclusion()

    def make_template_context(self, office):
        cases = [
            'nominativo',
            'vocativo',
            'accusativo',
            'genitivo',
            'dativo',
            'ablativo',
        ]

        prefix_map = {
            # XXX: Using keys[0] is wrong; factor out multi-key lookup so that
            # TemplateContext can use it too.
            'nomen_': office.keys[0] + '/nomen/',
            'nomen_titularis_': self._calendar_resolver.titular_path,
        }

        return parts.TemplateContext(
            direct_symbols={},
            indirect_symbols={
                prefix + case: path + case if path is not None else None
                for case in cases
                for (prefix, path) in prefix_map.items()
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
    preces_key = 'officium-defunctorum/preces'

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
