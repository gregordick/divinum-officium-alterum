# XXX: This module still has scars from the time when it tried to manage the
# keys for the various office-parts.

from abc import ABC, abstractmethod
import enum

from .util import roman


class Rite(enum.Enum):
    SIMPLE = 0
    SEMIDOUBLE = 1
    DOUBLE = 2
    GREATER_DOUBLE = 3


class Office(ABC):
    def __init__(self, desc):
        self.desc = dict(desc)

    def __str__(self):
        return "%s: %s" % (self.__class__.__name__, self.title())

    def __repr__(self):
        return str(self)

    def title(self):
        # XXX:
        return self.desc.get('titulus')

    @property
    def prefer_to_sundays(self):
        return False

    @property
    def universal(self):
        return True

    @property
    def rank(self):
        return self.desc['classis']

    @property
    def rite(self):
        return {
            'duplex majus': Rite.GREATER_DOUBLE,
            'duplex': Rite.DOUBLE,
            'semiduplex': Rite.SEMIDOUBLE,
            'simplex': Rite.SIMPLE,
        }[self.desc['ritus']]

    @property
    def key(self):
        return self.desc.get('titulus')


class ProperOfficeMixin:
    def __init__(self, desc):
        super().__init__(desc)
        self._root = 'proprium/%s' % (desc['titulus'],)

    def title(self):
        # XXX:
        return self._root


class Feast(ProperOfficeMixin, Office):
    @property
    def of_the_lord(self):
        return False


class TemporalOffice(Office):
    @property
    def week_num(self):
        return self.desc['hebdomada']


class Sunday(TemporalOffice):
    pass


class Feria(TemporalOffice):
    pass


class SundayPerAnnum(Sunday):
    pass


class SundayAfterPentecost(SundayPerAnnum):
    season = 'pent'

    def title(self):
        return "Dominica %s. post Pentecosten" % (roman(self.week_num),)


class AdventOfficeMixin:
    season = 'adv'

    def __init__(self, *args):
        super().__init__(*args)
        self.week_root = 'proprium/%s%d' % (self.season, self.week_num)
        # TODO: proprium or psalterium?
        self._season_root = 'proprium/%s' % (self.season,)


class AdventSunday(AdventOfficeMixin, Sunday):
    def vespers_psalms(self, is_first):
        return ('%s/ad-vesperas/antiphonae' % (self.week_root,),
                'psalterium/ad-vesperas/dominica/psalmi')

    def title(self):
        return "Dominica %s. Adventus" % (roman(self.week_num),)


class AdventFeria(AdventOfficeMixin, Feria):
    def title(self):
        return "Dominica %s. Adventus" % (roman(self.week_num),)


class ProperSunday(ProperOfficeMixin, Sunday):
    # XXX:
    season = 'nunquam'


class BVMOnSaturday(Feast): pass

class Vigil(Office): pass

class LentenFeria(Feria): pass

class WithinOctave(Office): pass
class OctaveDay(Office): pass
