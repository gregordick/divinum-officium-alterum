from officium.calendar import CalendarResolver, Resolution
from officium.offices import (
    BVMOnSaturday,
    Feast,
    Feria,
    LentenFeria,
    Sunday,
    Vigil,
    WithinOctave,
)

class CalendarResolver1962(CalendarResolver):
    # The vigil of the Epiphany had been abolished, allowing Nat2-0 to be
    # placed on 05 Jan.
    NAT2_SUNDAY_LIMIT = 5

    @staticmethod
    def _nat1_cond(date):
        # Nat1-0 falls on the Sunday in the octave.
        assert date.month == 12 and date.day > 25
        return date.day_of_week == 0

    @classmethod
    def _well_behaved_reading_date(cls, date):
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

    @staticmethod
    def occurrence_ranktie_resolution(a, b):
        assert a.rank == b.rank
        rank = a.rank

        # Ensure that the first office is a feast if we have any feasts.
        if not isinstance(a, Feast) and isinstance(b, Feast):
            a, b = b, a

        if rank == 1:
            # Certain first-class offices beat first-class Sundays.
            if a.prefer_to_sundays and isinstance(b, Sunday):
                a, b = b, a
            if b.prefer_to_sundays and isinstance(a, Sunday):
                return (b, Resolution.OMIT if isinstance(a, Vigil) else
                           Resolution.COMMEMORATE)

            # First-class feasts yield to first-class non-feasts (including
            # days in octaves), and are translated.
            if not isinstance(b, Feast):
                return (b, Resolution.TRANSLATE)

            # If two first-class feasts occur, a universal feast is preferred
            # to a particular one.
            if a.universal:
                a, b = b, a
            if b.universal and not a.universal:
                return (b, Resolution.TRANSLATE)

            # Otherwise, the feast of greater dignity wins.  TODO: Implement
            # this.
            return (b, Resolution.TRANSLATE)
        elif rank == 2:
            if isinstance(a, Feast):
                # A second-class feast beats a day in a second-class octave,
                # and likewise beats a second-class vigil.
                if isinstance(b, (WithinOctave, Vigil)):
                    return (a, Resolution.COMMEMORATE)
                elif isinstance(b, Feria):
                    # A second-class feast beats a second-class feria if and
                    # only if that feast is universal.
                    return (a if a.universal else b, Resolution.COMMEMORATE)

                if isinstance(b, Sunday):
                    return (b, Resolution.COMMEMORATE)

                # The only remaining possibility is that b is a feast.
                assert isinstance(b, Feast)

                # A universal second-class feast beats a particular such.
                if not b.universal:
                    a, b = b, a
                if b.universal:
                    return (b, Resolution.COMMEMORATE)

                # Two particular second-class feasts.  Movable beats fixed.
                # TODO: Implement this.
                assert not any([a.universal, b.universal])
                return (b, Resolution.COMMEMORATE)
            else:
                # No feasts.  This should happen only when a second-class
                # Sunday occurs with a second-class vigil.
                if isinstance(a, Sunday):
                    a, b = b, a
                if isinstance(a, Vigil) and isinstance(b, Sunday):
                    return (b, Resolution.OMIT)
                # Fall through to assertion at the bottom of the function.
        elif rank == 3:
            # a should always be a feast at this point.
            assert isinstance(a, Feast)

            if isinstance(b, Vigil):
                return (a, Resolution.COMMEMORATE)

            # Third-class feasts beat Advent ferias but yield to Lenten ones.
            if isinstance(b, Feria):
                return (b if isinstance(b, LentenFeria) else a,
                        Resolution.COMMEMORATE)

            assert isinstance(b, Feast)

            # Third-class particular feasts beat universal feasts, in contrast
            # to the second-class case.
            if not a.universal:
                a, b = b, a
            if a.universal:
                return (b, Resolution.COMMEMORATE)

            # A movable particular feast beats a fixed particular feast.  TODO:
            # Implement this.
            assert not any([a.universal, b.universal])
            return (b, Resolution.COMMEMORATE)
        else:
            # Fourth-class, which means commemorations, lesser ferias and the
            # Blessed Virgin Mary on Saturday.
            assert rank == 4
            for x in [a, b]:
                assert isinstance(x, (Feria, Feast))

            # BVM on Saturday always wins amongst fourth-class offices, and
            # takes the place of the feria.
            if isinstance(a, BVMOnSaturday):
                a, b = b, a
            if isinstance(b, BVMOnSaturday):
                return (b, Resolution.OMIT if isinstance(a, Feria) else
                           Resolution.COMMEMORATE)

            # In the absence of BVM on Saturday, the feria wins.
            if isinstance(a, Feria):
                return (a, Resolution.COMMEMORATE)
            else:
                assert isinstance(b, Feria)
                return (b, Resolution.COMMEMORATE)

        assert False, "Unexpected occurrence: (%r, %r)" % (a, b)

    @classmethod
    def occurrence_resolution(cls, a, b):
        if a.rank < b.rank:
            a, b = b, a
        if b.rank < a.rank:
            # The office of the Blessed Virgin Mary on Saturday is omitted when
            # it doesn't win.
            if isinstance(a, BVMOnSaturday):
                return (b, Resolution.OMIT)

            # Fourth-class ferias are never commemorated, and neither is any
            # feria on a first-class vigil.
            if (isinstance(a, Feria) and
                (a.rank == 4 or (isinstance(b, Vigil) and b.rank == 1))):
                return (b, Resolution.OMIT)

            privileged = isinstance(a, Sunday) or (isinstance(a, Feria) and
                                                   a.rank <= 3)

            # Unprivileged commemorations are omitted on Sundays and
            # first-class days.
            if (b.rank == 1 or isinstance(b, Sunday)) and not privileged:
                return (b, Resolution.OMIT)

            # Otherwise, commemorate.
            return (b, Resolution.COMMEMORATE)

        return cls.occurrence_ranktie_resolution(a, b)

    @classmethod
    def has_first_vespers(cls, office, date):
        if isinstance(office, Sunday):
            return True
        if isinstance(office, Feast):
            if office.rank == 1:
                return True
            if (office.rank == 2 and office.of_the_lord and
                date.day_of_week == 0):
                return True
        return False

    @classmethod
    def privileged_commemoration(cls, office, date):
        if office.rank == 1:
            return True
        if isinstance(office, Feria) and office.rank <= 3:
            return True
        if cls.has_first_vespers(office, date):
            # This catches Sundays, including feasts of the Lord on a Sunday.
            return True
        if isinstance(office, WithinOctave):
            # RG 108c: within the octave of Christmas, but this is equivalent.
            return True
        return False

    @classmethod
    def vespers_commem_filter(cls, commemorations, date, concurring):
        def privileged(office):
            office_date = date + 1 if office in concurring else date
            return cls.privileged_commemoration(office, office_date)
        return list(filter(privileged, commemorations))

    @classmethod
    def concurrence_resolution(cls, preceding, following, date):
        # Since we have concurrence at all, the following office must be a
        # Sunday (or a feast of the Lord behaving like a Sunday) or a
        # first-class feast.  The only way that the preceding office can win,
        # then, is if it's first-class or if it's a second-class feast and the
        # following is second-class (necessarily a Sunday).
        if preceding.rank == 1 or (preceding.rank == 2 and following.rank == 2):
            return (preceding, Resolution.COMMEMORATE)

        # Now we know that the following office wins, so we need only determine
        # whether to omit the preceding office, which happens if and only if
        # that office is not privileged in commemoration.
        if cls.privileged_commemoration(preceding, date):
            return (following, Resolution.COMMEMORATE)

        # Otherwise, office of the following, nothing of the preceding.  The
        # reverse situation never happens: when a day has first Vespers, it's
        # always privileged in commemoration.
        return (following, Resolution.OMIT)
