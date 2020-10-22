from officium import calendar

from flat_test_data import data_store

def test_easter():
    assert calendar.CalendarResolver.easter_sunday(2019) == calendar.Date(2019, 4, 21)

def test_2020_08_23():
    date = calendar.Date(2020, 8, 23)
