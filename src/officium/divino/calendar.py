from officium.offices import Rite, Standing
from officium.calendar import CalendarResolver, Resolution
from officium.offices import (
    AdventFeria,
    AdventSunday,
    BVMOnSaturday,
    Feast,
    Feria,
    LentenFeria,
    LentenSunday,
    OctaveDay,
    Sunday,
    SundayAfterPentecost,
    Vigil,
    WithinOctave,
)

class CalendarResolverDA(CalendarResolver):
    @staticmethod
    def dignity(office):
        # Conditions in order of decreasing dignity. Some of these are not
        # strictly necessary for the implementation, but are valid and help
        # testing.  TODO: Fill this out. See General Rubrics XI.2.
        conditions = [
            # Feasts of the Lord.
            isinstance(office, Feast) and office.of_the_lord,
            # Privileged octaves.
            office.octave_order <= 2,
            office.octave_order <= 3,
            # Everything else.
            True,
        ]
        return len(conditions) - conditions.index(True)

    @classmethod
    def subrank(cls, office):
        # For ties between third- or fourth-class days), we synthesise a
        # sub-rank.  Smaller is better.
        assert office.rank in [3, 4]

        # XXX: Eventually we'll make this common to pre-Divino; for
        # now, preserve the pre-Divino logic until we're ready to use
        # it.
        version = 1942
        return [
            isinstance(office, Sunday) and version > 1910,
            office.rite == Rite.GREATER_DOUBLE and
                isinstance(office, OctaveDay),
            office.rite == Rite.GREATER_DOUBLE,
            office.rite == Rite.DOUBLE,
            isinstance(office, Sunday) and version == 1910,
            office.rite == Rite.SEMIDOUBLE and isinstance(office, Feast),
            isinstance(office, Sunday) and version < 1910,
            isinstance(office, WithinOctave) and office.octave_order == 3,
            # Common octave.
            isinstance(office, WithinOctave),
            isinstance(office, Feria),
            isinstance(office, Vigil),
            isinstance(office, OctaveDay),
            isinstance(office, BVMOnSaturday),
            # The only remaining possibility is a simple feast.
            True,
        ].index(True)

    @classmethod
    def occurrence_ranktie_resolution(cls, a, b):
        assert a.rank == b.rank
        rank = a.rank

        if rank <= 2:
            # Sundays win.
            if isinstance(a, Sunday):
                a, b = b, a
            if isinstance(b, Sunday):
                return (b, Resolution.TRANSLATE)

            # At this point, at least one of the offices must be a feast, which
            # yields to all non-feasts (which must be a first-class vigil,
            # privileged feria or day within an octave of the appropriate
            # order).
            if isinstance(b, Feast):
                a, b = b, a
            if not isinstance(b, Feast):
                return (b, Resolution.TRANSLATE)

            # Must have two feasts now.
            return (max([a, b], key=cls.dignity), Resolution.TRANSLATE)
        else:
            # For the remaining possibilities (i.e. a tie between third- or
            # fourth-class days), we use the synthetic sub-rank.  Smaller is
            # better.
            a_subrank = cls.subrank(a)
            b_subrank = cls.subrank(b)
            if b_subrank > a_subrank:
                a, b = b, a
                a_subrank, b_subrank = b_subrank, a_subrank

            # The office of our Lady on Saturday is omitted if it doesn't win.
            if isinstance(a, BVMOnSaturday):
                return (b, Resolution.OMIT)

            if a_subrank != b_subrank:
                return (b, Resolution.COMMEMORATE)

            # If we're still tied, choose the feast of greater dignity.
            return (max([a, b], key=cls.dignity),
                    Resolution.TRANSLATE if rank <= 2 else
                    Resolution.COMMEMORATE)

    @classmethod
    def occurrence_resolution(cls, a, b):
        # Lesser ferias are always omitted in occurrence.  XXX: With simple
        # feasts and Ember Days and suchlike this becomes complicated... see
        # RG V.2.
        if isinstance(a, Feria) and a.standing == Standing.LESSER:
            a, b = b, a
        if isinstance(b, Feria) and b.standing == Standing.LESSER:
            return (a, Resolution.OMIT)

        # (Other) octaves cease in Lent and the two first-order octaves.
        def lent_or_first_order_octave(office):
            if isinstance(office, (LentenFeria, LentenSunday)):
                return True
            if (isinstance(office, (WithinOctave, OctaveDay)) and
                office.octave_order == 1):
                return True
            if isinstance(office, Vigil) and office.rank == 1:
                return True
            return False

        if lent_or_first_order_octave(a):
            a, b = b, a
        if (lent_or_first_order_octave(b) and
            isinstance(a, (WithinOctave, OctaveDay))):
            return (b, Resolution.OMIT)

        # Having dealt with the preceding exceptions, higher-ranked days always
        # win.
        if b.rank == a.rank:
            return cls.occurrence_ranktie_resolution(a, b)
        if a.rank < b.rank:
            a, b = b, a

        # At this point, b is the winner, but we need to find the resolution.

        # Second-class feasts yield to first-class days.
        if b.rank == 1 and a.rank == 2 and not isinstance(a, (Sunday,
                                                              WithinOctave)):
            resolution = Resolution.TRANSLATE

        # TODO: Transfer offices marked explicitly as transferrable.

        # Simple feasts and octave days are omitted on first-class doubles.
        elif (b.rank == 1 and
              b.rite >= Rite.DOUBLE and
              isinstance(b, Feast) and
              a.rite == Rite.SIMPLE and
              isinstance(a, (Feast, OctaveDay))):
            resolution = Resolution.OMIT

        # Furthermore, simple octave days are omitted on octave days of the
        # second order.  This is labelled as an impossible occurrence in the
        # table, but we'll handle it this way anyway.
        # XXX: Magic numbers.
        elif (isinstance(b, OctaveDay) and b.octave_order <= 2 and
              isinstance(a, OctaveDay) and a.octave_order == 5):
            resolution = Resolution.OMIT

        # Even greater ferias are omitted on I. cl. vigils.
        elif isinstance(a, Feria) and isinstance(b, Vigil) and b.rank == 1:
            resolution = Resolution.OMIT

        # Vigils are omitted on greater ferias and days that are genuinely of
        # the first class.  Also, we don't handle anticipation of vigils at
        # this point, so just omit them (other than the vigil of Christmas,
        # which we identify as being of the first class) on Sundays.
        elif (isinstance(a, Vigil) and
              (b.rank == 1 and isinstance(b, OctaveDay)) or
              (isinstance(b, Feria) and b.rank >= 3) or
              (isinstance(b, Sunday) and a.rank > 1)):
            resolution = Resolution.OMIT

        # The office of our Lady on Saturday is omitted if it doesn't win.
        elif isinstance(a, BVMOnSaturday):
            resolution = Resolution.OMIT

        # Days within common octaves are omitted on doubles of the first or
        # second class.  XXX: Magic number.
        elif (isinstance(a, WithinOctave) and a.octave_order == 4
              and b.rank <= 2 and b.rite >= Rite.DOUBLE and
              isinstance(b, Feast)):
            resolution = Resolution.OMIT

        else:
            resolution = Resolution.COMMEMORATE

        return (b, resolution);

    @classmethod
    def has_first_vespers(cls, office, date):
        # TODO: Need to be slightly careful about the vigil of the Epiphany
        # here.
        return not isinstance(office, (Vigil, Feria))

    @classmethod
    def has_second_vespers(cls, office, date):
        return all([
            not isinstance(office, Vigil),
            isinstance(office, Feria) or office.rite > Rite.SIMPLE,
            super().has_second_vespers(office, date),
        ])

    @classmethod
    def concurrence_rank(cls, office):
        # Synthetic rank in concurrence.  Smaller is better.  Sundays and
        # privileged octave days are in the same category.
        octave_day = isinstance(office, OctaveDay)
        double_non_octave = office.rite >= Rite.DOUBLE and not octave_day
        return [
             double_non_octave and office.rank == 1,
             double_non_octave and office.rank == 2,
             isinstance(office, Sunday) or
                (octave_day and office.octave_order <= 3),
            octave_day and office.octave_order == 4,
            office.rite == Rite.GREATER_DOUBLE,
            office.rite == Rite.DOUBLE,
            office.rite == Rite.SEMIDOUBLE and isinstance(office, Feast),
            isinstance(office, WithinOctave) and office.octave_order <= 3,
            isinstance(office, WithinOctave),
            isinstance(office, Feria) and office.standing >= Standing.GREATER,
            True
        ].index(True)

    @classmethod
    def concurrence_resolution(cls, preceding, following, date):
        preceding_conc_rank = cls.concurrence_rank(preceding)
        following_conc_rank = cls.concurrence_rank(following)

        if preceding_conc_rank < following_conc_rank:
            # Office of preceding. What to do with the following?

            # Find the rank of a faked-up day within a common octave.
            within_common_octave = cls.concurrence_rank(WithinOctave({
                'octavae_ordo': 4,
                'ritus': 'semiduplex',
            }))

            # Omit low-ranking days at first vespers of high-ranking doubles.
            if (preceding.rite == Rite.DOUBLE and preceding.rank <= 2 and
                following_conc_rank >= within_common_octave):
                resolution = Resolution.OMIT

            # Don't commemorate first vespers of the second day in the octave
            # in second vespers of the feast itself.
            elif (isinstance(following, WithinOctave) and
                  following.octave_id == preceding.octave_id):
                resolution = Resolution.OMIT

            else:
                resolution = Resolution.COMMEMORATE

            return (preceding, resolution)
        elif following_conc_rank < preceding_conc_rank:
            # Office of following.  Assume that we commemorate the preceding
            # unless we decide otherwise.
            resolution = Resolution.COMMEMORATE

            # Don't commemorate second vespers of seventh day in the octave at
            # first vespers of the octave day.  Notice that, since the
            # following office beat the preceding, we can't have concurrence of
            # two days in the octave here.
            if (isinstance(preceding, WithinOctave) and
                following.octave_id == preceding.octave_id):
                resolution = Resolution.OMIT

            # Check for some days that are low-ranking in concurrence but
            # nonetheless are always commemorated when they lose.
            elif ((isinstance(preceding, Feria) and
                   preceding.standing == Standing.GREATER) or
                  (isinstance(preceding, WithinOctave) and
                   preceding.octave_order <= 3)):
                assert resolution == Resolution.COMMEMORATE

            # Doubles of the I. or II. class cause low-ranking days to be
            # omitted in concurrence.
            elif following.rite == Rite.DOUBLE:
                if ((following.rank == 2 and
                     preceding_conc_rank >= cls.concurrence_rank(Feast(
                        {'ritus': 'semiduplex', 'classis': 3}
                     ))) or
                    (following.rank == 1 and
                     preceding_conc_rank >= cls.concurrence_rank(OctaveDay({
                        'ritus': 'duplex majus',
                        'classis': 3,
                        'octavae_ordo': 4,
                     })))):
                    resolution = Resolution.OMIT

            return (following, resolution)

        # Both days are in the same concurrence category.

        # In concurrence of days within the same octave, second vespers take
        # precedence and first vespers of the following are omitted.
        if (isinstance(following, WithinOctave) and
            following.octave_id == preceding.octave_id):
            return (preceding, Resolution.OMIT)

        # In a Sunday or privileged octave day vs. a privileged octave day or
        # vice versa, the office is always of the preceding.
        def privileged_octave_day(office):
            return (isinstance(office, OctaveDay) and
                    office.octave_order <= 3)
        if (any(privileged_octave_day(x) for x in [preceding, following]) and
            all(privileged_octave_day(x) or isinstance(x, Sunday)
                for x in [preceding, following])):
            return (preceding, Resolution.COMMEMORATE)

        # Office of the day of greater dignity; or, in parity, from the chapter
        # of the following.
        dignity_preceding = cls.dignity(preceding)
        dignity_following = cls.dignity(following)
        if dignity_preceding > dignity_following:
            return (preceding, Resolution.COMMEMORATE)
        elif dignity_following > dignity_preceding:
            return (following, Resolution.COMMEMORATE)
        else:
            # From the chapter.  We report the preceding as the winner here,
            # since the bit of the office for the preceding comes first.
            return (preceding, Resolution.FROM_THE_CHAPTER)

    @classmethod
    def fill_implicit_descriptor_fields(cls, desc_class, desc):
        if 'classis' not in desc:
            # XXX: This is a bit unpleasant, inferring things directly from the
            # descriptor as it does, and duplicates some things that live in
            # offices.py.
            octave_order = int(desc.get('octavae_ordo', 6))
            if isinstance(desc_class, Sunday):
                rank = 2 if re.match(r'ma[ij]or', desc['status']) else 3
            elif isinstance(desc_class, Feria):
                rank = (1 if re.match(r'privilegiata', desc['status']) else
                        3 if re.match(r'ma[ij]or', desc['status']) else 4)
            elif isinstance(desc_class, Feast):
                rank = 4 if desc['ritus'] == 'simplex' else 3
            elif isinstance(desc_class, OctaveDay):
                rank = 1 if octave_order <= 2 else 3 if octave_order <= 4 else 4
            elif isinstance(desc_class, WithinOctave):
                rank = min(octave_order, 3)
            else:
                rank = 4
            desc['classis'] = rank

    @classmethod
    def can_transfer(cls, transfer_office, offices):
        # We can place the transferred office on this day if the day is free of
        # first- and second-class offices, or if the office is one of a few
        # singled out in the rubrics, and it would win in occurrence.  (TODO:
        # Handle that last bit.)
        return all(office.rank > 2 for office in offices)
