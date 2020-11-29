from officium.calendar import CalendarResolver, Resolution

class CalendarResolverDA(CalendarResolver):
    @classmethod
    def occurrence_resolution(cls, a, b):
        return (b, Resolution.COMMEMORATE)
