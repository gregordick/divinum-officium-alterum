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
            'ad-i-vesperas' if is_first else 'ad-ii-vesperas',
            'ad-vesperas',
        ]
        return self._data_map.lookup(self.lookup_order(
            office, ('%s/%s' % (b, item) for item in items for b in base)))

    def lookup_main(self, *items):
        return self.lookup(self._office, self._is_first, *items)

    def resolve(self):
        yield parts.deus_in_adjutorium()

        antiphons = self.lookup_main('antiphonae')
        psalms = self.lookup_main('psalmi')
        psalms = self._data_map[psalms]
        yield parts.Group(
            parts.PsalmishWithAntiphon('{}/{}'.format(antiphons, n), psalms)
            for (n, psalms) in enumerate(psalms)
        )

        yield parts.Chapter([parts.Text(self.lookup_main('capitulum'))])
        # XXX: Not just Text here.
        yield parts.Hymn([parts.Text(self.lookup_main('hymnus'))])
        versicle_pair = self.lookup_main('versiculum')
        yield parts.Versicle([parts.Text(versicle_pair + '/0')])
        yield parts.VersicleResponse([parts.Text(versicle_pair + '/1')])

        mag_ant = self.lookup_main('ad-magnificat')
        # XXX: Slashes.
        yield parts.PsalmishWithAntiphon(mag_ant,
                                         ['psalterium/ad-vesperas/magnificat'])

        # Oration.
        yield parts.Group([
            parts.dominus_vobiscum(),
            parts.Oration([parts.Text(self.lookup_main('oratio'))]),
        ])

        # Commemorations.
        for commem in self._commemorations:
            is_first = commem in self._concurring
            versicle_pair = self.lookup(commem, is_first, 'versiculum')
            yield parts.Group([
                parts.Antiphon(self.lookup(commem, is_first, 'ad-magnificat')),
                parts.Versicle([parts.Text(versicle_pair + '/0')]),
                parts.VersicleResponse([parts.Text(versicle_pair + '/1')]),
                parts.Oration([parts.Text(self.lookup(commem, is_first,
                                                      'oratio'))]),
            ])

        # Conclusion.
        yield parts.Group([
            parts.dominus_vobiscum(),
            parts.Versicle([parts.Text('versiculi/benedicamus-domino')]),
            parts.VersicleResponse([parts.Text('versiculi/deo-gratias')]),
            parts.Versicle([parts.Text('versiculi/fidelium-animae')]),
            parts.VersicleResponse([parts.Text('versiculi/amen')]),
        ])
