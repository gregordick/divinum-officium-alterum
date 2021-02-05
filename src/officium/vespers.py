from . import parts
from . import util

class Vespers:
    def __init__(self, date, data_map, office, concurring, commemorations):
        self._date = date
        self._data_map = data_map
        self._office = office
        self._is_first = office in concurring

        # Knowing the concurring offices allows us to determine whether a
        # commemoration is for first Vespers.
        self._concurring = concurring

        self._commemorations = list(commemorations)

    def lookup_order(self, office, items):
        paths = [
            lambda item: 'proprium/%s/%s' % (office.key, item),
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
        return self._data_map.lookup(self.lookup_order(
            office, ('/'.join(b + [item]) for item in items for b in base)))

    def lookup_main(self, *items):
        return self.lookup(self._office, self._is_first, *items)

    def resolve(self):
        yield parts.deus_in_adjutorium()

        antiphons = self.lookup_main('antiphonae')
        psalms = self.lookup_main('psalmi')
        psalms = self._data_map[psalms]
        yield parts.Psalmody(antiphons, psalms)

        yield parts.StructuredLookup(self.lookup_main('capitulum'),
                                     parts.Chapter)
        yield parts.StructuredLookup(self.lookup_main('hymnus'),
                                     parts.Hymn)
        versicle_pair = self.lookup_main('versiculum')
        # XXX: Extend StructuredLookup to take a richer implicit structure,
        # so that it can convert a two-element list into a versicle and a
        # response.
        yield parts.StructuredLookup(versicle_pair + '/0', parts.Versicle)
        yield parts.StructuredLookup(versicle_pair + '/1', parts.VersicleResponse)

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
                parts.StructuredLookup(versicle_pair + '/0', parts.Versicle),
                parts.StructuredLookup(versicle_pair + '/1', parts.VersicleResponse),
                parts.StructuredLookup(self.lookup(commem, is_first, 'oratio'),
                                       parts.Oration),
            ])

        # Conclusion.
        yield parts.Group([
            parts.dominus_vobiscum(),
            parts.StructuredLookup('versiculi/benedicamus-domino',
                                   parts.Versicle),
            parts.StructuredLookup('versiculi/deo-gratias',
                                   parts.VersicleResponse),
            parts.StructuredLookup('versiculi/fidelium-animae', parts.Versicle),
            parts.StructuredLookup('versiculi/amen', parts.VersicleResponse),
        ])
