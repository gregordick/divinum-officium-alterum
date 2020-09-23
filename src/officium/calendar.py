import calendar as stdlib_calendar
import datetime
import itertools
import re

from . import offices
from .vespers import Vespers


BVM_SATURDAY_CALPOINT = 'SMariaeInSabbato'


class Date(datetime.date):
    def __new__(cls, year, month=None, day=None):
        return super().__new__(cls, year, month, day)

    # pylint: disable=unused-argument
    def __init__(self, *args, **kwargs):
        super().__init__()
        self._day_of_week = self.isoweekday() % 7

    @classmethod
    def from_datetime_date(cls, date):
        return cls(date.year, date.month, date.day)

    def __add__(self, days):
        base_result = super().__add__(datetime.timedelta(days=days))
        return self.from_datetime_date(base_result)

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


class CalendarResolver:
    # Latest date in January on which Nat2-0 can fall.  This value is correct
    # for most versions, but can be overridden in others.
    NAT2_SUNDAY_LIMIT = 4

    def __init__(self, data_map):
        self._data_map = data_map

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

        # Find the (one-based) index of the week within the reading month.  By
        # well-behavedness, this is equal to to the week within the calendar
        # month.
        week = (well_behaved.day - 1) // 7 + 1

        # Special handling for November: the second week vanishes most years
        # (and always with the 1962 rubrics, owing to the later earliest
        # possible start of the month).  Achieve this by counting backwards
        # from Advent.
        if month == 11 and week >= 2:
            advent = cls.advent_sunday(date.year)
            assert date < advent
            week = 5 - (advent - date - 1) // 7

        return (month, week, date.day_of_week)

    @classmethod
    def temporal_week(cls, date):
        # Round down to Sunday.
        sunday = date - date.day_of_week

        # The temporal cycle reanchors itself to Sundays on the first Sunday
        # after Epiphany.
        epiphany = Date(date.year, 6, 1)
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
        reading_day = self.reading_day(date)
        if reading_day is not None:
            calpoints.append('%02d%d-%d' % reading_day)

        # Last x-day.
        if date.day_of_week == 0 and days_in_month - date.day < 7:
            calpoints.append('%s%s-Ult' % (month_prefix,
                                           days[date.day_of_week]))

        # Temporal cycle, except for Christmas-Epiphany.
        week = self.temporal_week(date)
        if week is not None:
            calpoints.append('%s-%s' % (week, date.day_of_week))

        if self.is_sunday_in_christmas_octave(date):
            calpoints.append('Nat1-0')
        elif self.is_sunday_after_christmas_octave(date):
            calpoints.append('Nat2-0')

        # Office of our Lady on Saturday.
        if date.day_of_week == 6:
            calpoints.append(BVM_SATURDAY_CALPOINT)

        return calpoints

    def calpoint_offices(self, calpoint):
        calentry = 'calendarium/%s' % (calpoint,)
        if calentry in self._data_map:
            office_list = []
            for descriptor in self._data_map[calentry]:
                # TODO: It needn't be a feast.
                root = '%s/%s' % (calpoint, descriptor.get('titulus', calpoint))
                office_list.append(offices.Feast(root))
            return office_list

        # If there was nothing explicit, fall back to any autogenerated
        # office(s).
        m = re.match(r'Pent(\d+)-0$', calpoint)
        if m:
            return [offices.SundayAfterPentecostOffice(int(m.group(1)))]

        return []

    def offices(self, date, calendar):
        calpoints = self.generate_calpoints(date)
        desc = list(itertools.chain.from_iterable(self.calpoint_offices(c)
                                                  for c in calpoints))[0]
        return [Vespers(date, self._data_map, is_first=False, occurring=[desc],
                        concurring=[])]


class CalendarResolver1962(CalendarResolver):
    # The vigil of the Epiphany had been abolished, allowing Nat2-0 to be
    # placed on 05 Jan.
    NAT2_SUNDAY_LIMIT = 5

    @staticmethod
    def _nat1_cond(date):
        # Nat1-0 falls on the Sunday in the octave.
        assert date.month == 12 and date.day > 25
        return date.day_of_week == 0

    def _well_behaved_reading_date(self, date):
        # The week of the month is defined to be the week _in_ the month, so
        # the weakly-preceding Sunday is well-behaved.
        return date - date.day_of_week

    def reading_day(self, date):
        (month, week, dow) = super().reading_day(date)

        # The third week of October vanishes in years when its Sunday would
        # otherwise fall on the 18th-21st (i.e. when the first Sunday in
        # October falls on 4th-7th).
        if month == 10 and week >= 3:
            first_sunday = date - date.day_of_week - (week - 1) * 7
            if first_sunday.day >= 4:
                assert first_sunday.day <= 7
                week += 1

        return (month, week, dow)
