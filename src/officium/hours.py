from . import vespers

class Hours:
    """Maps hours to classes."""

    def __init__(self, first_vespers, second_vespers):
        self.first_vespers = first_vespers
        self.second_vespers = second_vespers


hours_map = {
    'octavae-paschalis':
        Hours(
            first_vespers=vespers.HolySaturdayVespers,
            second_vespers=vespers.EasterOctaveVespers,
        ),
    'defunctorum':
        Hours(
            first_vespers=vespers.VespersOfTheDead,
            second_vespers=vespers.VespersOfTheDead,
        ),
    'communis':
        Hours(
            first_vespers=vespers.Vespers,
            second_vespers=vespers.Vespers,
        ),
}
