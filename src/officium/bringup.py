import yaml

from officium.calendar import Date
from officium.data import Data
from officium.divino.calendar import CalendarResolverDA
from officium.rubricarum.calendar import CalendarResolver1962


resolvers = {
    'rubricarum': CalendarResolver1962,
    'divino':     CalendarResolverDA,
}


def make_date(date_str):
    return Date(*(int(x) for x in date_str.split('-')))


def merge_records(data, records):
    for record in records:
        assert len(record) == 2
        if record[0] == 'create':
            data.create(record[1])
        elif record[0] == 'append':
            data.append(record[1])
        elif record[0] == 'redirect':
            data.redirect(record[1])
        else:
            assert False, record[0]


def make_data(*base_dicts):
    data = Data({})
    for d in base_dicts:
        data.create(d)
    return data


def make_generic(rubrics, raw_generic):
    generic = {
        'proprium/dominica-resurrectionis/ad-i-vesperas/psalmi': [['psalmi/116']],
    }
    data = make_data(resolvers[rubrics].base_calendar(), generic)
    merge_records(data, raw_generic)
    return data


def make_latin(raw_latin):
    latin = {
        'versiculi/deus-in-adjutorium': 'Deus, in adjutórium meum inténde.',
        'versiculi/domine-ad-adjuvandum': 'Dómine, ad adjuvándum me festína.',
        'versiculi/gloria-patri': 'Glória Patri, et Fílio, et Spirítui Sancto.',
        'versiculi/sicut-erat': 'Sicut erat in princípio, et nunc, et semper, et in sǽcula sæculórum.  Amen.',
        'versiculi/alleluja': 'Allelúja.',
        'versiculi/laus-tibi-domine': 'Laus tibi, Dómine, Rex ætérnæ glóriæ.',
        'formula-alleluia-simplicis': 'allel[uú][ij]a',
        'proprium/dominica-resurrectionis/ad-i-vesperas/antiphonae': ['Allelúja, * allelúja, allelúja.'],
        'proprium/ss-soteris-et-caji-paparum-et-martyrum/nomen/genitivo': [
            'Sotéris',
            'Caji',
        ],
    }

    data = make_data(latin)
    merge_records(data, raw_latin)
    return data


# XXX: Latin is special here, but only because we're building the index, which
# in principle should be external.
def bringup_components(generic_file, latin_data_file, rubrics, titular_path):
    with open(generic_file) as f:
        raw_generic = yaml.load(f, Loader=yaml.CSafeLoader)
    with open(latin_data_file) as f:
        raw_latin_data = yaml.load(f, Loader=yaml.CSafeLoader)

    data = make_generic(rubrics, raw_generic)
    latin_data = make_latin(raw_latin_data)
    index = make_data(data.dictionary, latin_data.dictionary)
    for key in index.dictionary:
        index.dictionary[key] = 'INDEX'
    # XXX: Redirections shouldn't be in latin_data.
    index.redirections = dict(data.redirections, **latin_data.redirections)

    resolver = resolvers[rubrics](data, index, titular_path)

    return resolver, latin_data
