from abc import ABC, abstractmethod

from .util import roman


class Office(ABC):
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


class SundayOffice(Office):
    def __init__(self, week_num):
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


class SundayPerAnnumOffice(SundayOffice):
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


class SundayAfterPentecostOffice(SundayPerAnnumOffice):
    _season = 'pent'

    def title(self):
        return "Dominica %s. post Pentecosten" % (roman(self._week_num),)


class Feast(Office):
    def __init__(self, root):
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
        pass
