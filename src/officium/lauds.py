from . import psalmish
# XXX!  Most of vespers.py should become a common module.
from .vespers import LaudsAndVespers


class Lauds(LaudsAndVespers):
    def lookup(self, office, *items, **kwargs):
        bases = [
            ['ad-laudes'],
        ]
        return super().lookup(office, bases, *items, **kwargs)

    @property
    def gospel_canticle_path(self):
        # XXX: Slashes.
        return 'ad-laudes/benedictus'

    def have_ferial_preces(self):
        return self._calendar_resolver.has_ferial_preces(self._office,
                                                         self._date)


class EasterOctaveLauds(Lauds):
    # TODO
    pass


class LaudsOfTheDead(Lauds):
    # TODO
    pass


class TriduumLauds(Lauds):
    default_psalmish_class = psalmish.PsalmishWithoutGloria
    # TODO
