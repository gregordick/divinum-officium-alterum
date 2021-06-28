# XXX: This module still has scars from the time when it tried to manage the
# keys for the various office-parts.

from .util import roman


class Rite:
    SIMPLE = 0
    SEMIDOUBLE = 1
    DOUBLE = 2
    GREATER_DOUBLE = 3


class Standing:
    LESSER = 0
    GREATER = 1
    GREATER_PRIVILEGED = 2


class Office:
    extra_keys = []

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
            'duplex maius': Rite.GREATER_DOUBLE,
            'duplex': Rite.DOUBLE,
            'semiduplex': Rite.SEMIDOUBLE,
            'simplex': Rite.SIMPLE,
        }[self.desc['ritus'].replace('j', 'i')]

    @property
    def keys(self):
        return ['proprium/%s' % (self.desc.get('titulus'),)] + self.extra_keys

    @property
    def standing(self):
        return {
            'maior privilegiata': Standing.GREATER_PRIVILEGED,
            'maior': Standing.GREATER,
            'minor': Standing.LESSER,
        }[self.desc.get('status', 'minor').replace('j', 'i')]

    @property
    def octave_order(self):
        # XXX: There should be an intermedite human-ish layer here, as for the
        # other things above.  Note that we synthesise a descriptor containing
        # the octavae_ordo field in at least one place, so fix that/those up
        # too.
        return int(self.desc.get('octavae_ordo', 6))


class Feast(Office):
    @property
    def of_the_lord(self):
        return False


# XXX: Having TemporalOffice in the class hierarchy is wrong, because some
# types of office (feasts, vigils, ...) can be temporal or sanctoral.
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
    def title(self):
        return "Dominica %s. post Pentecosten" % (roman(self.week_num),)


class AdventSunday(Sunday):
    def title(self):
        return "Dominica %s. Adventus" % (roman(self.week_num),)


class AdventFeria(Feria):
    def title(self):
        return "Dominica %s. Adventus" % (roman(self.week_num),)


class BVMOnSaturday(Feast): pass

class Vigil(Office): pass

class SeptuagesimatideFeria(Feria): pass
class SeptuagesimatideSunday(Sunday): pass

class LentenFeria(Feria):
    extra_keys = [
        'proprium/de-tempore/quadragesima/in-feriis',
        'proprium/de-tempore/quadragesima',
    ]

# For Ash Wednesday and the three following days.  XXX: This is a bit ugly.
class EarlyLentenFeria(LentenFeria):
    extra_keys = []

class LentenSunday(Sunday):
    extra_keys = [
        'proprium/de-tempore/quadragesima',
    ]

class PassiontideFeria(LentenFeria):
    extra_keys = [
        'proprium/de-tempore/passionis/in-feriis',
        'proprium/de-tempore/passionis',
    ]

class PassiontideSunday(LentenSunday):
    extra_keys = [
        'proprium/de-tempore/passionis',
    ]

class WithinOctave(Office): pass
class OctaveDay(Office): pass
