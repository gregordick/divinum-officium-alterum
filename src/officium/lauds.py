from . import psalmish

# XXX!  Most of vespers.py should become a common module.
from .vespers import Vespers
class Lauds(Vespers):
    def __init__(self, *args):
        args = list(args)
        super().__init__(*args[:-1], concurring=[], commemorations=args[-1])


class EasterOctaveLauds(Lauds):
    # TODO
    pass


class LaudsOfTheDead(Lauds):
    # TODO
    pass


class TriduumLauds(Lauds):
    default_psalmish_class = psalmish.PsalmishWithoutGloria
    # TODO
