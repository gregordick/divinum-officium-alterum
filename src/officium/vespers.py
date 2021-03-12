from . import offices
from . import parts
from . import psalmish
from . import util

class Vespers:
    def __init__(self, date, generic_data, index, calendar_resolver, office,
                 concurring, commemorations):
        self._date = date
        self._generic_data = generic_data
        self._index = index
        self._calendar_resolver = calendar_resolver
        self._office = office
        self._is_first = office in concurring

        # Knowing the concurring offices allows us to determine whether a
        # commemoration is for first Vespers.
        self._concurring = concurring

        self._commemorations = list(commemorations)

    def lookup_order(self, office, items):
        paths = [
            lambda item, key=key: '%s/%s' % (key, item)
            for key in office.keys
        ]
        # Fall back to propers from the preceding Sunday.  XXX: This is wrong,
        # in two respects: firstly, it should be any non-Sunday temporal
        # office, and not necessarily a feria; and secondly, slicing and dicing
        # the first key is in very poor taste.
        if isinstance(office, offices.Feria):
            sunday = office.keys[0][:-1] + '0'
            paths.append(lambda item: 'proprium/%s/%s' % (sunday, item))
        paths += [
            lambda item: 'psalterium/%s/%s' % (util.day_ids[self._date.day_of_week],
                                               item),
            lambda item: 'psalterium/%s' % (item,),
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

    def resolve(self):
        easter = self._calendar_resolver.easter_sunday(self._date.year)
        alleluia = not (easter - 7 * 9 <= self._date < easter)
        yield parts.deus_in_adjutorium(alleluia)

        antiphons = self.lookup_main('antiphonae')
        psalms = self.lookup_main('psalmi')
        yield parts.Psalmody(antiphons, self._generic_data[psalms])

        yield parts.StructuredLookup(self.lookup_main('capitulum'),
                                     parts.Chapter)
        yield parts.StructuredLookup(self.lookup_main('hymnus'),
                                     parts.Hymn)
        versicle_pair = self.lookup_main('versiculum')
        yield parts.StructuredLookup(versicle_pair, parts.VersicleWithResponse)

        path = self.lookup_main('ad-magnificat')
        mag_ant = parts.StructuredLookup(path, parts.Antiphon)
        # XXX: Slashes.
        mag = psalmish.PsalmishWithGloria('ad-vesperas/magnificat')
        yield parts.PsalmishWithAntiphon(mag_ant, [mag])

        # Oration.
        oration_path = self.lookup_main('oratio-super-populum', 'oratio')
        oration = parts.StructuredLookup(oration_path, parts.Oration)
        yield parts.Group([
            parts.dominus_vobiscum(),
            parts.oremus(),
            oration,
            parts.oration_conclusion(oration_path, self._generic_data),
            parts.amen(),
        ])

        # Commemorations.
        for i, commem in enumerate(self._commemorations):
            is_first = commem in self._concurring
            versicle_pair = self.lookup(commem, is_first, 'versiculum')
            oration_path = self.lookup(commem, is_first,
                                       'oratio-super-populum', 'oratio')
            part_list = [
                parts.StructuredLookup(self.lookup(commem, is_first,
                                                   'ad-magnificat'),
                                       parts.Antiphon),
                parts.StructuredLookup(versicle_pair,
                                       parts.VersicleWithResponse),
                parts.oremus(),
                parts.StructuredLookup(oration_path, parts.Oration),
            ]
            # Only the last commemoration gets the conclusion.
            if i == len(self._commemorations) - 1:
                part_list += [
                    parts.oration_conclusion(oration_path, self._generic_data),
                    parts.amen(),
                ]
            yield parts.Group(part_list)

        # Conclusion.
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
