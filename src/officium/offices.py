from abc import ABC, abstractmethod
import enum

from .util import roman


class Rite(enum.Enum):
    SIMPLE = 0
    SEMIDOUBLE = 1
    DOUBLE = 2
    GREATER_DOUBLE = 3


class Office(ABC):
    def __init__(self, rank):
        self.rank = rank

    def __str__(self):
        return "%s: %s" % (self.__class__.__name__, self.title())

    def __repr__(self):
        return str(self)

    @abstractmethod
    def vespers_psalms(self, is_first):
        pass

    @abstractmethod
    def vespers_chapter(self, is_first):
        pass

    @abstractmethod
    def vespers_hymn(self, is_first):
        pass

    @abstractmethod
    def vespers_versicle(self, is_first):
        pass

    @abstractmethod
    def magnificat_antiphon(self, is_first):
        pass

    @abstractmethod
    def oration(self):
        pass

    @abstractmethod
    def title(self):
        pass

    @property
    def prefer_to_sundays(self):
        return False

    @property
    def universal(self):
        return True

    @property
    @abstractmethod
    def rite(self):
        pass


class Sunday(Office):
    def __init__(self, week_num, rank):
        super().__init__(rank)
        self._week_num = week_num

    @property
    @classmethod
    @abstractmethod
    def _season(cls):
        pass

    @property
    def _week(self):
        return '%s-%d' % (self._season, self._week_num)

    def magnificat_antiphon(self, is_first):
        return 'proprium/%s/ad-magnificat' % (self._week,)

    def oration(self):
        return 'proprium/%s/oratio' % (self._week,)

    @property
    def rite(self):
        return Rite.SEMIDOUBLE


class SundayPerAnnum(Sunday):
    def vespers_psalms(self, is_first):
        return ('psalterium/ad-vesperas/dominica/antiphonae',
                'psalterium/ad-vesperas/dominica/psalmi')

    def vespers_chapter(self, is_first):
        # Not Sunday-specific.
        return 'psalterium/ad-vesperas/dominica/capitulum'

    def vespers_hymn(self, is_first):
        return 'psalterium/ad-vesperas/dominica/hymnus'

    def vespers_versicle(self, is_first):
        # Not Sunday-specific.
        return 'psalterium/ad-vesperas/dominica/versiculum'


class SundayAfterPentecost(SundayPerAnnum):
    _season = 'pent'

    def __init__(self, *args):
        super().__init__(*args, rank=2)

    def title(self):
        return "Dominica %s. post Pentecosten" % (roman(self._week_num),)


class Feast(Office):
    def __init__(self, root, rank):
        super().__init__(rank)
        self._root = 'proprium/%s' % (root,)

    def vespers_psalms(self, is_first):
        path = '%s/ad-vesperas' % (self._root,)
        return ('%s/antiphonae' % (path,), '%s/psalmi' % (path,))

    def vespers_chapter(self, is_first):
        return '%s/ad-vesperas/capitulum' % (self._root,)

    def vespers_hymn(self, is_first):
        return '%s/ad-vesperas/hymnus' % (self._root,)

    def vespers_versicle(self, is_first):
        return '%s/ad-vesperas/versiculum' % (self._root,)

    def magnificat_antiphon(self, is_first):
        return '%s/ad-magnificat' % (self._root,)

    def oration(self):
        return '%s/oratio' % (self._root,)

    def title(self):
        # XXX:
        return self._root

    @property
    def of_the_lord(self):
        return False

    @property
    def rite(self):
        # XXX:
        return Rite.DOUBLE

class BVMOnSaturday(Feast): pass

class Vigil(Office): pass

class Feria(Office): pass
class LentenFeria(Feria): pass
class AdventFeria(Feria): pass

class WithinOctave(Office): pass
class OctaveDay(Office): pass
