from . import offices
from . import parts
from . import util

class Vespers:
    def __init__(self, date, generic_data, index, office, concurring,
                 commemorations):
        self._date = date
        self._generic_data = generic_data
        self._index = index
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
        yield parts.deus_in_adjutorium()

        antiphons = self.lookup_main('antiphonae')
        psalms = self.lookup_main('psalmi')
        psalms = self._generic_data[psalms]
        yield parts.Psalmody(antiphons, psalms)

        yield parts.StructuredLookup(self.lookup_main('capitulum'),
                                     parts.Chapter)
        yield parts.StructuredLookup(self.lookup_main('hymnus'),
                                     parts.Hymn)
        versicle_pair = self.lookup_main('versiculum')
        yield parts.StructuredLookup(versicle_pair, parts.VersicleWithResponse)

        path = self.lookup_main('ad-magnificat')
        mag_ant = parts.StructuredLookup(path, parts.Antiphon)
        # XXX: Slashes.
        yield parts.PsalmishWithAntiphon(mag_ant,
                                         ['psalterium/ad-vesperas/magnificat'])

        # Oration.
        yield parts.Group([
            parts.dominus_vobiscum(),
            parts.StructuredLookup(self.lookup_main('oratio'), parts.Oration),
        ])

        # Commemorations.
        for commem in self._commemorations:
            is_first = commem in self._concurring
            versicle_pair = self.lookup(commem, is_first, 'versiculum')
            yield parts.Group([
                parts.StructuredLookup(self.lookup(commem, is_first,
                                                   'ad-magnificat'),
                                       parts.Antiphon),
                parts.StructuredLookup(versicle_pair,
                                       parts.VersicleWithResponse),
                parts.StructuredLookup(self.lookup(commem, is_first, 'oratio'),
                                       parts.Oration),
            ])

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
