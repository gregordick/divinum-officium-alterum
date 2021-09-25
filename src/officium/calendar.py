from abc import ABC, abstractmethod
import calendar as stdlib_calendar
from collections import OrderedDict
import datetime
import enum
import itertools
import re

from . import offices
from . import hours


BVM_SATURDAY_CALPOINT = 'SMariaeInSabbato'


class Date(datetime.date):
    # pylint: disable=unused-argument
    def __init__(self, *args, **kwargs):
        super().__init__()
        self._day_of_week = self.isoweekday() % 7

    def __add__(self, days):
        base_result = super().__add__(datetime.timedelta(days=days))
        return Date(base_result.year, base_result.month, base_result.day)

    def __sub__(self, days_or_date):
        if isinstance(days_or_date, self.__class__):
            return super().__sub__(days_or_date).days
        return self + (-days_or_date)

    @property
    def day_of_week(self):
        """Returns the index of the day of the week, starting from Sunday at
        zero.
        """
        return self._day_of_week


class Resolution(enum.Enum):
    FROM_THE_CHAPTER = enum.auto()
    COMMEMORATE = enum.auto()
    OMIT = enum.auto()
    TRANSLATE = enum.auto()
    APPEND = enum.auto()


class CalendarResolver(ABC):
    # Latest date in January on which Nat2-0 can fall.  This value is correct
    # for most versions, but can be overridden in others.
    NAT2_SUNDAY_LIMIT = 4

    def __init__(self, data_map, index):
        self._data_map = data_map
        self._index = index

        # XXX: Temporary crude cache to make regression tests faster.
        self._resolve_transfer_cache = None
        self._resolve_transfer_cache_base = None

    @staticmethod
    def advent_sunday(year):
        """Returns the date of the first Sunday of Advent for the specified
        year.
        """
        christmas_eve = Date(year, 12, 24)
        advent4 = christmas_eve - christmas_eve.day_of_week
        return advent4 - 7 * 3

    @staticmethod
    def _nat1_cond(date):
        # Place Nat1-0 on 30 Dec if that day lies in Tues-Fri, and otherwise on
        # the Sunday that falls within the octave.
        assert date.month == 12 and date.day > 25
        return ((date.day >= 29 and date.day_of_week == 0) or
                (date.day == 30 and date.day_of_week in [2, 3, 4, 5]))

    @classmethod
    def is_sunday_in_christmas_octave(cls, date):
        return date.month == 12 and date.day > 25 and cls._nat1_cond(date)

    @classmethod
    def is_sunday_after_christmas_octave(cls, date):
        if date.month != 1:
            return False

        # If there's a Sunday between 02 Jan and the limit, that's the day.
        if (date.day_of_week == 0 and date.day >= 2 and
                date.day <= cls.NAT2_SUNDAY_LIMIT):
            return True

        # In other years, it's on 02 Jan.
        if (date.day == 2 and date.day_of_week >= 1 and
                date.day_of_week <= 8 - cls.NAT2_SUNDAY_LIMIT):
            return True

        return False

    # pylint: disable=invalid-name,too-many-locals
    @staticmethod
    def easter_sunday(year):
        """Returns the date of Easter Sunday in the Gregorian calendar,
        calculated using the algorithm in "A New York correspondent", "To find
        Easter", Nature 338 (1876), p. 487.
        """
        a = year % 19
        b, c = divmod(year, 100)
        d, e = divmod(b, 4)
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i, k = divmod(c, 4)
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451
        n = h + l - 7 * m + 114
        month, day = divmod(n, 31)
        day += 1
        assert 1 <= month <= 12, month
        assert day <= stdlib_calendar.monthrange(year, month)[1], (day, month)
        return Date(year, month, day)

    @classmethod
    def _well_behaved_reading_date(cls, date):
        """Returns a date in the same reading week as the specified date, but
        with the properties that its calendar month is equal to its reading
        month, and that its calendar month-week is equal to its reading
        month-week.
        """
        # When reading-months start with Kalends, the Wednesday of the current
        # week has the properties that we want.
        return date - date.day_of_week + 3

    @classmethod
    def reading_day(cls, date):
        """Returns a (month, week, day-of-week) tuple identifying the "reading
        day" for Matins for the specified date (e.g. (8, 4, 2) for the Tuesday
        in the fourth week of August) or None when this does not apply.
        """
        # Find a well-behaved day for the current week, whose reading-month is
        # its calendar-month.
        well_behaved = cls._well_behaved_reading_date(date)
        month = well_behaved.month

        # The reading months are August to November inclusive.
        if month not in range(8, 12):
            return None
        advent = cls.advent_sunday(date.year)
        if date >= advent:
            return None

        # Find the (one-based) index of the week within the reading month.  By
        # well-behavedness, this is equal to to the week within the calendar
        # month.
        week = (well_behaved.day - 1) // 7 + 1

        # Special handling for November: the second week vanishes most years
        # (and always with the 1962 rubrics, owing to the later earliest
        # possible start of the month).  Achieve this by counting backwards
        # from Advent.
        if month == 11 and week >= 2:
            week = 5 - (advent - date - 1) // 7

        return (month, week, date.day_of_week)

    @classmethod
    def reading_day_str(cls, date):
        reading_day = cls.reading_day(date)
        return '%02d%d-%d' % reading_day if reading_day is not None else None

    @classmethod
    def temporal_week(cls, date):
        # Round down to Sunday.
        sunday = date - date.day_of_week

        # The temporal cycle reanchors itself to Sundays on the first Sunday
        # after Epiphany.
        epiphany = Date(date.year, 1, 6)
        if sunday <= epiphany:
            return None

        easter = cls.easter_sunday(date.year)
        septuagesima = easter - 9 * 7

        # Sundays after Epiphany.
        if sunday < septuagesima:
            return "Epi%d" % ((sunday - epiphany + 6) // 7,)

        # Septuagesima and Lent.
        lent1 = easter - 6 * 7
        if sunday < lent1:
            return "Quadp%d" % ((sunday - septuagesima) // 7 + 1,)
        if sunday < easter:
            return "Quad%d" % ((sunday - lent1) // 7 + 1,)

        # Paschaltide.
        pentecost = easter + 7 * 7
        if sunday <= pentecost:
            return "Pasc%d" % ((sunday - easter) // 7,)

        # Sundays after Pentecost, up to and including the twenty-second, after
        # which things get complicated.
        pent22 = pentecost + 22 * 7
        if sunday <= pent22:
            return "Pent%d" % ((sunday - pentecost) // 7,)

        advent = cls.advent_sunday(date.year)

        # The office of the twenty-fourth Sunday after Pentecost is always kept
        # on the Sunday before Advent, even when there are only twenty-three
        # Sundays after Pentecost.  Any Sundays after the twenty-third and
        # before the last are filled with the Sundays remaining after Epiphany.
        pent_last = advent - 7
        if sunday < pent_last:
            if sunday == pent22 + 7:
                return "Pent23"
            return "Epi%d" % (7 - (pent_last - sunday) // 7,)

        # Last Sunday after Pentecost and Advent.  From Christmas Eve, the
        # day in the temporal cycle is determined by the calendar date.
        christmas_eve = Date(date.year, 12, 24)
        if date < christmas_eve:
            if sunday < advent:
                assert sunday == pent_last
                return "Pent24"
            else:
                return "Adv%d" % ((sunday - advent) // 7 + 1,)
        else:
            return None

    @classmethod
    def temporal_calpoint(cls, date):
        week = cls.temporal_week(date)
        if week:
            return "%s-%d" % (week, date._day_of_week)
        return None

    def generate_calpoints(self, date):
        days = [
            'Dominica',
            'FeriaII',
            'FeriaIII',
            'FeriaIV',
            'FeriaV',
            'FeriaVI',
            'Sabbato',
        ]

        month_prefix = '%02d-' % (date.month,)
        days_in_month = stdlib_calendar.monthrange(date.year, date.month)[1]

        calpoints = [
            # Calendar day: mm-dd.
            month_prefix + '%02d' % (date.day,),

            # nth x-day _in_ the month.
            '%s%s-%d' % (
                month_prefix,
                days[date.day_of_week],
                date.day // 7 + 1,
            ),
        ]

        # nth x-day _of_ the month.
        reading_day = self.reading_day_str(date)
        if reading_day is not None:
            calpoints.append(reading_day)

        # Last x-day.
        if date.day_of_week == 0 and days_in_month - date.day < 7:
            calpoints.append('%s%s-Ult' % (month_prefix,
                                           days[date.day_of_week]))

        # Temporal cycle, except for Christmas-Epiphany.
        calpoint = self.temporal_calpoint(date)
        if calpoint is not None:
            calpoints.append(calpoint)

            # Office of our Lady on Saturday.
            if date.day_of_week == 6:
                calpoints.append(BVM_SATURDAY_CALPOINT)
        else:
            if self.is_sunday_in_christmas_octave(date):
                calpoints.append('Nat1-0')
            elif self.is_sunday_after_christmas_octave(date):
                calpoints.append('Nat2-0')

        return calpoints

    @classmethod
    def season(cls, calpoint_season, week, day):
        if calpoint_season == 'Quadp':
            # XXX: Ash Wednesday and the following three days don't behave like
            # Lenten days in all respects, so some care will be needed here.
            # Maybe fix them up in the calendar?
            if week == 3 and day >= 3:
                return 'quad'
            return 'septuagesimae'
        if calpoint_season == 'Quad' and week >= 5:
            return 'passionis'
        return calpoint_season.lower()

    @classmethod
    def split_calpoint(cls, calpoint):
        # TODO: Use named groups here.
        m = re.match(r'(Pent|Adv|Nat|Epi|Quadp|Quad|Pasc)(\d+)-([0-6])$',
                     calpoint)
        if m:
            return (m.group(1), int(m.group(2)), int(m.group(3)))
        return None, None, None

    @classmethod
    def default_descriptor(cls, calpoint):
        desc = {
            'titulus': calpoint,
        }
        calpoint_season, week, day = cls.split_calpoint(calpoint)
        if calpoint_season:
            desc['tempus'] = cls.season(calpoint_season, week, day)
            desc['hebdomada'] = week
            if desc['tempus'] in ['quad', 'passionis']:
                desc['status'] = 'major'
            if day == 0:
                desc['qualitas'] = 'dominica'
                desc['ritus'] = 'semiduplex'
            else:
                desc['qualitas'] = 'feria'
                desc['feria'] = day
                desc['ritus'] = 'simplex'
            return desc
        else:
            return None

    @classmethod
    def base_calendar(cls):
        return {
            'calendarium/%s' % (calpoint,): [cls.default_descriptor(calpoint)]
            for calpoint in itertools.chain(
                ('Adv%d-%d' % (week, day)
                 for week in range(1, 5) for day in range(7)),
                ('Epi%d-%d' % (week, day)
                 for week in range(1, 7) for day in range(7)),
                ('Quadp%d-%d' % (week, day)
                 for week in range(1, 4) for day in range(7)),
                ('Quad%d-%d' % (week, day)
                 for week in range(1, 7) for day in range(7)),
                ('Pasc%d-%d' % (week, day)
                 for week in range(8) for day in range(7)),
                ('Pent%d-%d' % (week, day)
                 for week in range(1, 25) for day in range(7)),
            )
        }

    sunday_classes = {
        'adv': offices.AdventSunday,
        'pent': offices.SundayAfterPentecost,
        'septuagesimae': offices.SeptuagesimatideSunday,
        'quad': offices.LentenSunday,
        'passionis': offices.PassiontideSunday,
    }

    feria_classes = {
        'adv': offices.AdventFeria,
        'septuagesimae': offices.SeptuagesimatideFeria,
        'quad': offices.LentenFeria,
        'passionis': offices.PassiontideFeria,
    }

    @classmethod
    def descriptor_class(cls, desc):
        if desc['qualitas'] == 'festum':
            return offices.Feast
        elif desc['qualitas'] == 'dominica':
            try:
                return cls.sunday_classes[desc['tempus']]
            except KeyError:
                return offices.Sunday
        elif desc['qualitas'] == 'feria':
            return cls.feria_classes.get(desc.get('tempus'), offices.Feria)
        elif desc['qualitas'] == 'infra-octavam':
            return offices.WithinOctave
        elif desc['qualitas'] == 'dies-octava':
            return offices.OctaveDay
        elif desc['qualitas'] == 'vigilia':
            return offices.Vigil
        elif desc['qualitas'] == 'officium sanctae mariae in sabbato':
            return offices.BVMOnSaturday
        elif desc['qualitas'] == 'defunctorum':
            return offices.OfTheDead
        assert False, desc['qualitas']

    @classmethod
    def fill_implicit_descriptor_fields(cls, desc):
        pass

    def calpoint_offices(self, calpoint):
        calentry = 'calendarium/%s' % (calpoint,)
        default_desc = self.default_descriptor(calpoint)
        descriptors = self._data_map.get(calentry, [])
        office_list = []
        for descriptor in descriptors:
            if default_desc is not None:
                descriptor = dict(default_desc, **descriptor)
            desc_class = self.descriptor_class(descriptor)
            self.fill_implicit_descriptor_fields(desc_class, descriptor)
            office = desc_class(descriptor)
            office_list.append(office)
        return office_list

    @staticmethod
    @abstractmethod
    def occurrence_resolution(a, b):
        # Override this method.
        raise NotImplementedError()

    def resolve_occurrence(self, date):
        calpoints = self.generate_calpoints(date)
        offices = itertools.chain.from_iterable(self.calpoint_offices(c)
                                                for c in calpoints)
        resolver = self
        class OccurrenceOrderer:
            def __init__(self, office):
                self.office = office

            def __lt__(self, other):
                resolution = resolver.occurrence_resolution(self.office,
                                                            other.office)
                return resolution[0] is self.office

        ordered = list(sorted(offices, key=OccurrenceOrderer))
        assert ordered, calpoints
        return ordered

    def resolve_commemorations(self, occurring, concurring=[]):
        # XXX: Support generators?  And sort!
        return occurring + concurring

    @classmethod
    @abstractmethod
    def has_first_vespers(cls, a, b):
        # Override this method.
        raise NotImplementedError()

    @classmethod
    def has_second_vespers(cls, office, date):
        # Child classes should override this method and add further exceptions.
        return not office.second_vespers_suppressed

    @classmethod
    def vespers_commem_filter(cls, commemorations, date, concurring):
        return commemorations

    @classmethod
    @abstractmethod
    def can_transfer(cls, transfer_office, offices):
        # Override this method.
        raise NotImplementedError()

    def resolve_transfer(self, start, end):
        assert start <= end

        # XXX: Temporary external caching mechanism.
        if self._resolve_transfer_cache_base is not None:
            start_delta = start - self._resolve_transfer_cache_base
            end_delta = end - self._resolve_transfer_cache_base
            if (start_delta >= 0 and
                end_delta - start_delta < len(self._resolve_transfer_cache)):
                return [list(x) for x in self._resolve_transfer_cache[start_delta:end_delta + 1]]

        # Offices can be transferred by up to a year, so start from a year ago.
        current = start - 366
        transfer = []
        result = []

        # Round down to a Sunday.  TODO: Implement the resumption and
        # anticipation of Sundays.
        while current.day_of_week != 0:
            current -= 1
        while current <= end:
            offices = self.resolve_occurrence(current)
            if transfer and self.can_transfer(transfer[0], offices):
                offices = [transfer[0]] + offices
                transfer = transfer[1:]

            # If any tail offices should be transferred, add them to the
            # transfer list.
            def versus_other(other):
                _, resolution = self.occurrence_resolution(offices[0], other)
                return resolution
            new_transfers = [x for x in offices[1:]
                             if versus_other(x) == Resolution.TRANSLATE]
            if new_transfers:
                transfer += new_transfers

            # Remove any offices that have been transferred away from this day,
            # and also any that are omitted in occurrence with the winner.
            offices = [offices[0]] + [x for x in offices[1:]
                                      if x not in new_transfers]

            # Note that at this point we do _not_ filter out any offices that
            # will be omitted in occurrence.  This is because this is not
            # well-defined until we fix the hour: for example, a feria can
            # reappear at Vespers after having been omitted during the office
            # of an occurring simple feast.

            if current >= start:
                result.append(offices)
            current += 1

        return result

    @classmethod
    def hour_classes(cls, office):
        return hours.hours_map[office.hours_key]

    def offices(self, date):
        today, tomorrow = self.resolve_transfer(date, date + 1)

        # Find evening offices.
        occurring = [office for office in today
                     if self.has_second_vespers(office, date)]
        concurring = [office for office in tomorrow
                      if self.has_first_vespers(office, date + 1)]

        assert occurring or concurring, (date, today, tomorrow)

        # Filter out omitted offices.
        for offices in [today, tomorrow, occurring, concurring]:
            if offices:
                offices[:] = [offices[0]] + [
                    office for office in offices[1:]
                    if self.occurrence_resolution(offices[0], office)[1] !=
                    Resolution.OMIT
                ]

        # Arbitrate between occurring and concurring.
        if occurring and concurring:
            office, _ = self.concurrence_resolution(occurring[0], concurring[0],
                                                    date)
        elif occurring:
            office = occurring[0]
        else:
            assert concurring, date
            office = concurring[0]

        second_vespers = office in occurring

        # Should we keep an office that concurs with this one?
        def keep(other):
            args = (office, other) if second_vespers else (other, office)
            args += (date,)
            _, resolution = self.concurrence_resolution(*args)
            return resolution != Resolution.OMIT

        # Find the commemorations.
        if second_vespers:
            occurring_commem = occurring[1:]
            concurring_commem = list(filter(keep, concurring))
        else:
            assert office is concurring[0]
            concurring_commem = occurring[1:]
            occurring_commem = list(filter(keep, occurring))

        # Sort the commemorations.
        commemorations = self.resolve_commemorations(occurring_commem,
                                                     concurring_commem)

        season = None
        calpoint = self.temporal_calpoint(date)
        if calpoint:
            season, _, _ = self.split_calpoint(calpoint)
            season = season.lower()

        # Get seasonal keys, which in practice means the months from August to
        # November.  These are strictly weekly, so only for Sundays do we have
        # first Vespers.
        reading_day = self.reading_day_str(date + 1 if date.day_of_week == 6
                                           else date)
        season_keys = [reading_day] if reading_day else []

        vespers_offices = [office]
        # Handle the case where two offices are said together.  We assume that
        # this can only happen when the office is of the preceding.
        if (occurring and concurring and
            office is occurring[0] and
            concurring[0] in commemorations):
            _, resn = self.concurrence_resolution(office, concurring[0], date)
            if resn == Resolution.APPEND:
                vespers_offices.append(concurring[0])
                commemorations = [c for c in commemorations
                                  if c is not concurring[0]]

        hour_classes = self.hour_classes(office)
        vespers_classeses = [self.hour_classes(x) for x in vespers_offices]
        vespers_classes = [
            vc.second_vespers if ofc in occurring else vc.first_vespers
            for (vc, ofc) in zip(vespers_classeses, vespers_offices)
        ]

        return OrderedDict([
            ('vespers', [cls(date, self._data_map, self._index, self, season,
                             season_keys, vespers_office, concurring,
                             self.vespers_commem_filter(commemorations, date,
                                                        concurring))
                         for (cls, vespers_office) in zip(vespers_classes,
                                                          vespers_offices)]),
        ])
