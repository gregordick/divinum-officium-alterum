from . import lauds
from . import vespers

class Hours:
    """Maps hours to classes."""

    def __init__(self, first_vespers, lauds, second_vespers):
        self.first_vespers = first_vespers
        self.lauds = lauds
        self.second_vespers = second_vespers


hours_map = {
    'octavae-paschalis':
        Hours(
            first_vespers=vespers.HolySaturdayVespers,
            lauds=lauds.EasterOctaveLauds,
            second_vespers=vespers.EasterOctaveVespers,
        ),
    'defunctorum':
        Hours(
            first_vespers=vespers.VespersOfTheDead,
            lauds=lauds.LaudsOfTheDead,
            second_vespers=vespers.VespersOfTheDead,
        ),
    'communis':
        Hours(
            first_vespers=vespers.Vespers,
            lauds=lauds.Lauds,
            second_vespers=vespers.Vespers,
        ),
    'tridui-sacri':
        Hours(
            # XXX: first_vespers is a nonsense here.
            first_vespers=vespers.TriduumVespers,
            lauds=lauds.TriduumLauds,
            second_vespers=vespers.TriduumVespers,
        ),
}
