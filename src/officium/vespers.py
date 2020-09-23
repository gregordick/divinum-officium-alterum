from . import parts

class Vespers:
    def __init__(self, date, data_map, is_first, occurring, concurring):
        self._date = date
        self._data_map = data_map
        self._is_first = is_first
        self._occurring = occurring
        self._concurring = concurring
        self._office = concurring[0] if is_first else occurring[0]

    def resolve(self):
        yield parts.deus_in_adjutorium()

        antiphons, psalms = self._office.vespers_psalms(self._is_first)
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

        yield parts.Group([
            parts.dominus_vobiscum(),
            parts.Oration([parts.Text(self._office.oration())]),
        ])
        yield parts.Group([
            parts.dominus_vobiscum(),
            parts.Versicle([parts.Text('versiculi/benedicamus-domino')]),
            parts.VersicleResponse([parts.Text('versiculi/deo-gratias')]),
            parts.Versicle([parts.Text('versiculi/fidelium-animae')]),
            parts.VersicleResponse([parts.Text('versiculi/amen')]),
        ])
