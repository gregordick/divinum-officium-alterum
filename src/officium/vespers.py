from . import parts
from . import util

class Vespers:
    def __init__(self, date, data_map, is_first, occurring, concurring,
                 commemorations):
        self._date = date
        self._data_map = data_map
        self._is_first = is_first

        # Find the winning office, and keep lists of all _other_
        # occurring/concurring offices.
        self._occurring = list(occurring)
        self._concurring = list(concurring)
        day_offices = self._concurring if is_first else self._occurring
        self._office = day_offices.pop(0)

        self._commemorations = list(commemorations)
        assert all(commem in self._occurring + self._concurring
                   for commem in self._commemorations)

    def resolve(self):
        yield parts.deus_in_adjutorium()

        antiphons, psalms = self._office.vespers_psalms(self._is_first)
        if psalms not in self._data_map:
            day = util.day_ids[self._date.day_of_week]
            base = 'psalterium/ad-vesperas/%s/' % (day,)
            psalms = base + 'psalmi'
            # XXX: It's not valid to assume that antiphons are from the psalter
            # whenever the psalms are.
            antiphons = base + 'antiphonae'
        psalms = self._data_map[psalms]
        yield parts.Group(
            parts.PsalmishWithAntiphon('{}/{}'.format(antiphons, n), psalms)
            for (n, psalms) in enumerate(psalms)
        )

        yield parts.Chapter([parts.Text(self._office.vespers_chapter(self._is_first))])
        # XXX: Not just Text here.
        yield parts.Hymn([parts.Text(self._office.vespers_hymn(self._is_first))])
        versicle_pair = self._office.vespers_versicle(self._is_first)
        yield parts.Versicle([parts.Text(versicle_pair + '/0')])
        yield parts.VersicleResponse([parts.Text(versicle_pair + '/1')])

        mag_ant = self._office.magnificat_antiphon(self._is_first)
        # XXX: Slashes.
        yield parts.PsalmishWithAntiphon(mag_ant,
                                         ['psalterium/ad-vesperas/magnificat'])

        # Oration.
        yield parts.Group([
            parts.dominus_vobiscum(),
            parts.Oration([parts.Text(self._office.oration())]),
        ])

        # Commemorations.
        for commem in self._commemorations:
            is_first = commem in self._concurring
            versicle_pair = commem.vespers_versicle(is_first)
            yield parts.Group([
                parts.Antiphon(commem.magnificat_antiphon(is_first)),
                parts.Versicle([parts.Text(versicle_pair + '/0')]),
                parts.VersicleResponse([parts.Text(versicle_pair + '/1')]),
                parts.Oration([parts.Text(commem.oration())]),
            ])

        # Conclusion.
        yield parts.Group([
            parts.dominus_vobiscum(),
            parts.Versicle([parts.Text('versiculi/benedicamus-domino')]),
            parts.VersicleResponse([parts.Text('versiculi/deo-gratias')]),
            parts.Versicle([parts.Text('versiculi/fidelium-animae')]),
            parts.VersicleResponse([parts.Text('versiculi/amen')]),
        ])
