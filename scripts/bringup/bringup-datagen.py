#!/usr/bin/env python3

"""Script to generate bringup datafiles from protoype calcalc calendar and DO
datafiles.
"""

# XXX: Some of this is pretty unpleasant.

import argparse
import itertools
import os
import re
import sys

import yaml

from officium import bringup
from officium import calendar
from officium import offices
from officium import util


def do_rubric_expression_matches(expression, do_rubric_name):
    return do_rubric_name.lower() in expression.lower()


def dict_list_append(the_dict, key, value):
    the_dict.setdefault(key, []).append(value)


def add_rubric(desc, rubric):
    dict_list_append(desc, 'rubricae', rubric)


def terminatur_post_nonam(desc):
    add_rubric(desc, 'officium terminatur post nonam')


def make_do_basename(calpoint):
    do_calpoint = re.sub(r'Pent(\d)-', r'Pent0\1-', calpoint)
    return os.path.join(
        'Sancti' if re.match(r'\d\d-\d\d$', calpoint) else 'Tempora',
        do_calpoint,
    )


def make_descriptor(key, calcalc_lines, do_rubric_name):
    desc = {}

    # Handle inline conditionals.  Block conditionals were handled by the
    # caller.
    filtered = []
    for line in calcalc_lines:
        line = line.strip()
        m = re.match(r'[(](.*)[)]\s*(.*)$', line)
        if m:
            condition, body = m.groups()
            assert body, "Block conditional? %s" % (line,)
            condition = condition.strip()
            if not do_rubric_expression_matches(condition, do_rubric_name):
                continue
            if condition.startswith('sed'):
                assert filtered, line
                filtered.pop()
            line = body
        filtered.append(line)
    calcalc_lines = filtered
    if not calcalc_lines:
        return

    if calcalc_lines and not calcalc_lines[0].startswith('rank='):
        desc['titulus'] = re.sub(r'\W+', '-', calcalc_lines.pop(0).lower())

    # Find the rankline.
    rankline = None
    while calcalc_lines:
        rankline = calcalc_lines.pop(0)
        if '(sed' not in rankline:
            if rankline.startswith('rank='):
                rankline = rankline[5:]
            if '=' not in rankline:
                break
        print(rankline, file=sys.stderr)
    else:
        rankline = None

    if rankline:
        if rankline.startswith('rank='):
            rankline = rankline[5:]

        if rankline.endswith('IV. classis'):
            desc['classis'] = 4
        elif rankline.endswith('III. classis'):
            desc['classis'] = 3
        elif rankline.endswith('II. classis'):
            desc['classis'] = 2
        elif rankline.endswith('I. classis'):
            desc['classis'] = 1

        if 'Duplex maius' in rankline:
            desc['ritus'] = 'duplex majus'
        elif 'Semiduplex' in rankline:
            desc['ritus'] = 'semiduplex'
        elif 'Duplex' in rankline:
            desc['ritus'] = 'duplex'
        else:
            desc['ritus'] = 'simplex'

        if 'Festum Domini' in rankline:
            desc['persona'] = 'dominus'

        if key.endswith(calendar.BVM_SATURDAY_CALPOINT):
            desc['qualitas'] = 'officium sanctae mariae in sabbato'
        elif key.endswith('11-02'):
            desc['qualitas'] = 'defunctorum'
        elif rankline.startswith('Festum'):
            desc['qualitas'] = 'festum'
        elif rankline.startswith('Dominica'):
            desc['qualitas'] = 'dominica'
        elif rankline.startswith('Feria'):
            desc['qualitas'] = 'feria'
        elif rankline.startswith('Dies infra'):
            desc['qualitas'] = 'infra-octavam'
        elif rankline.startswith('Dies oct'):
            desc['qualitas'] = 'dies-octava'
        elif rankline.startswith('Vigilia'):
            desc['qualitas'] = 'vigilia'
        else:
            assert False, (desc, rankline, calcalc_lines)

        if re.search(r'privilegiata', rankline, flags=re.I):
            desc['status'] = 'major privilegiata'
        elif re.search(r'ma[ji]or', rankline, flags=re.I):
            desc['status'] = 'major'

        m = re.search(r'octavam? (I+\. ordinis|communis|simplex)', rankline)
        if m:
            desc['octavae_ordo'] = {
                'I. ordinis': 1,
                'II. ordinis': 2,
                'III. ordinis': 3,
                'communis': 4,
                'simplex': 5,
            }[m.group(1)]
    else:
        # No rankline.
        desc['qualitas'] = 'dominica' if key.endswith('-0') else 'feria'

    for remaining_line in calcalc_lines:
        if remaining_line.startswith('octid='):
            desc['octavae_nomen'] = remaining_line[6:].lower()
        elif remaining_line.startswith('file='):
            desc['do_basename'] = remaining_line[5:].lower()
        elif remaining_line == 'Officium terminatur post Nonam':
            terminatur_post_nonam(desc)

    desc.setdefault('do_basename', make_do_basename(key.removeprefix('calendarium/')))

    if re.search(r'Quad6-[456]', key):
        desc['officium'] = 'tridui-sacri'
    if 'Pasc0' in key:
        desc['officium'] = 'octavae-paschalis'

    festum_bmv = re.search(r'mari(æ|ae)-(virg|in-sabbato)',
                           desc.get('titulus', ''))
    if 'persona' not in desc and festum_bmv:
        desc['persona'] = 'beata-maria-virgo'

    doxology = None
    if desc.get('octavae_nomen') == 'nat':
        doxology = calendar.CalendarResolver.doxology_path('nativitatis')
    elif desc.get('octavae_nomen') == 'epi':
        doxology = calendar.CalendarResolver.doxology_path('epiphaniae')
    elif festum_bmv:
        doxology = calendar.CalendarResolver.doxology_path('nativitatis')
    else:
        doxology = calendar.CalendarResolver.calpoint_doxology(key)
    if doxology:
        desc['doxologia'] = doxology

    if key.endswith('093-6') or (do_rubric_name != '1960' and
                                 re.search(r'093-[35]$', key)):
        terminatur_post_nonam(desc)

    assert len(desc) > 1 or desc.get('qualitas') != 'feria'
    yield desc


def make_descriptors(key, calcalc_lines, do_rubric_name):
    # Split the lines by blank lines.
    lines = []
    yielded = False
    drop = False
    for line in calcalc_lines:
        if line:
            if line.startswith('@'):
                drop = True
            if not drop:
                lines.append(line)
        else:
            if lines and not drop:
                yield from make_descriptor(key, lines, do_rubric_name)
                yielded = True
            drop = False
            lines = []
    if lines or not yielded:
        yield from make_descriptor(key, lines, do_rubric_name)


def expand_calendar_at_refs(raw_do_calendar):
    def expand(lines):
        for line in lines:
            if line.startswith('@:'):
                yield from expand(raw_do_calendar[line[2:]])
            else:
                yield line
    return {k: list(expand(v)) for (k, v) in raw_do_calendar.items()}


do_rubric_names = {
    'rubricarum': '1960',
    'divino': 'Divino',
}

def _parse(f, options, do_rubric_name, section_regex):
    raw = {}
    # Completely spurious parser, but good enough.
    rubric_squashed = False
    section = None
    accumulator = ''
    for line in f:
        line = line.rstrip()

        if line.endswith('~'):
            accumulator += line[:-1] + ' '
            continue

        # Block conditionals.  XXX: This isn't complete.  Consider handling
        # this after having read in all sections.
        if re.match(r'[(].*[)]$', line):
            cond_matches = do_rubric_expression_matches(line, do_rubric_name)
            if 'omittitur' in line:
                if cond_matches:
                    while section and section.pop() != '':
                        pass
            elif 'omittuntur' in line:
                # XXX: Should only clobber as far back as the beginning of the
                # nested scope.
                if cond_matches:
                    section = []
            else:
                rubric_squashed = not (
                     cond_matches or
                    'deinde' in line
                )
                if rubric_squashed and options.verbose:
                    print('SQUASH:', line, file=sys.stderr)
            continue

        m = re.match(section_regex + '.*' + do_rubric_name, line, re.I)
        if not m:
            m = re.match(section_regex + '$', line)
        if m:
            section = raw[m.group(1)] = []
            rubric_squashed = False
            continue
        elif line.startswith('['):
            section = None
        elif accumulator:
            line = accumulator + line
            accumulator = ''

        assert not accumulator, "Section ends with continuation"

        line = re.sub(r'\b([VRvr]|Ant)[.] ', '', line)

        if not rubric_squashed and section is not None:
            section.append(line)

    # Trim trailing blank lines.
    for section in raw:
        while raw[section] and not raw[section][-1]:
            raw[section].pop()

    return raw


def parse(filename, options, do_rubric_name):
    if 'Ordinarium' in filename:
        section_regex = '#(.*)'
    else:
        section_regex = r'\[(.*)\]'
    with open(filename, 'r') as f:
        return _parse(f, options, do_rubric_name, section_regex)


def make_calendar(raw, do_rubric_name):
    d = {
        'calendarium/' + k: list(make_descriptors('calendarium/' + k, v,
                                                  do_rubric_name))
        for (k, v) in expand_calendar_at_refs(raw).items()
    }

    if do_rubric_name == 'Divino':
        assert d['calendarium/07-24'].pop(0)['titulus'] == 'in-vigilia-s-jacobi-apostoli'
        # An error in the parser for conditionals means that we skip this one anyway:
        #assert d['calendarium/09-20'].pop(1)['titulus'] == 'in-vigilia-s-matthaei-apostoli'
        assert d['calendarium/11-08'].pop(0)['titulus'] == 'in-octava-omnium-sanctorum'
        assert d['calendarium/11-29'].pop(0)['titulus'] == 'in-vigilia-s-andreae-apostoli'

    # Split the entries into those that should replace default entries and
    # those that should be appended.
    create = {}
    append = {}
    for (key, entries) in d.items():
        calpoint = key[len('calendarium/'):]
        if calpoint in ['093-3', '093-5', '093-6']:
            append[key] = entries
        else:
            # This is very ad hoc: Sundays and ferias are easy, but we also
            # want to catch the temporal octaves.  XXX: What about the octave
            # of the Epiphany, and any sanctoral offices that happen to fall
            # within it?
            temporal = [x for x in entries
                        if x['qualitas'] in ['dominica', 'feria'] or
                           re.match(r'Pasc[0567]', calpoint)]
            others = [x for x in entries if x not in temporal]
            if temporal:
                create[key] = temporal
            if others:
                append[key] = others

    output = []
    if create:
        output.append(['create', create])
    if append:
        output.append(['append', append])

    return output

suffrage_map = {
    '1': 'de-beata-maria-atque-omnibus-sanctis',
    '2': 'de-cruce/ad-laudes',
    '2v': 'de-cruce/ad-vesperas',
    '11': 'de-omnibus-sanctis',
}

warn_keys = {}
def make_out_key(key, do_basename):
    versicle_keys = [
        'Oremus',
    ]
    post_process_keys = [
        'Benedicamus Domino',
        'Dominus',
        'Fidelium animae',
        'Per Dominum',
        'Per eundem',
        'Qui vivis',
        'Qui tecum',
        'Per Dominum eiusdem',
        'Qui tecum eiusdem',
        'Pater_noster1',
        ('Commune/C9', 'Oratio 21'),
        ('Commune/C9', 'Conclusio'),
        ('Commune/C9', 'Oratio_Fid'),
    ] + [
        'Suffragium%s' % (k,) for k in suffrage_map
    ]
    if key is None:
        return None
    elif key == 'Ant 1':
        out_key = 'ad-i-vesperas/ad-canticum'
    elif key == 'Ant 2':
        out_key = 'ad-laudes/ad-canticum'
    elif key == 'Ant 3':
        out_key = 'ad-ii-vesperas/ad-canticum'
    elif re.match(r'Ant (Vespera|Laudes)', key):
        if key == 'Ant Laudes':
            out_key = 'ad-laudes'
        elif key == 'Ant Vespera 1':
            out_key = 'ad-i-vesperas'
        elif key == 'Ant Vespera 3':
            out_key = 'ad-ii-vesperas'
        else:
            out_key = 'ad-vesperas'
        out_key += '/antiphonae'
    elif key == 'Oratio 1':
        out_key = 'ad-i-vesperas/oratio'
    elif key == 'Oratio 3':
        if 'Quad' in do_basename:
            out_key = 'oratio-super-populum'
        else:
            out_key = 'ad-ii-vesperas/oratio'
    elif key == 'Oratio':
        out_key = 'oratio'
    elif key == 'Capitulum Vespera 1':
        out_key = 'ad-i-vesperas/capitulum'
    elif key == 'Capitulum Vespera 3':
        out_key = 'ad-ii-vesperas/capitulum'
    elif key == 'Capitulum Vespera':
        out_key = 'ad-vesperas/capitulum'
    elif key == 'Hymnus Vespera 1':
        out_key = 'ad-i-vesperas/hymnus'
    elif key == 'Hymnus Vespera 3':
        out_key = 'ad-ii-vesperas/hymnus'
    elif key == 'Hymnus Vespera':
        out_key = 'ad-vesperas/hymnus'
    elif key == 'Versum 1':
        out_key = 'ad-i-vesperas/versiculum'
    elif key == 'Versum 3':
        out_key = 'ad-ii-vesperas/versiculum'
    elif key == 'Versum 2' and 'Pasc0-' in do_basename:
        out_key = 'haec-dies'
    elif re.match(r'Day\d (Laudes[12]?|Vespera)$', key):
        day = int(key[3])
        hour = ('vesperas' if key.endswith('Vespera') else
                'laudes'   if key.endswith('Laudes1') else
                'laudes-ii')
        # This key is either the chapter or the antiphons and psalms, depending
        # on which file it came from.
        part = ('capitulum' if do_basename.endswith('Major Special')
                else 'antiphonae')
        out_key = f'psalterium/{util.day_ids[day]}/ad-{hour}/{part}'
    elif re.match(r'Hymnus Day(\d) (Laudes\d?|Vespera)$', key):
        day = int(key[10])
        hour = 'ad-laudes' if 'Laudes' in key else 'ad-vesperas'
        base = 'psalterium'
        if key.endswith('Day0 Laudes'):
            # As opposed to Day0 Laudes2.
            base += '/in-aestate'
        out_key = f'{base}/{util.day_ids[day]}/{hour}/hymnus'
    elif key == 'Quad Vespera':
        out_key = 'proprium/de-tempore/quadragesima/in-feriis/ad-vesperas/capitulum'
    elif key == 'Hymnus Quad Vespera':
        out_key = 'proprium/de-tempore/quadragesima/ad-vesperas/hymnus'
    elif key == 'Quad Versum 3':
        out_key = 'proprium/de-tempore/quadragesima/ad-vesperas/versiculum'
    elif key == 'Quad5 Versum 3':
        out_key = 'proprium/de-tempore/passionis/ad-vesperas/versiculum'
    elif key == 'Hymnus Quad5 Vespera':
        out_key = 'proprium/de-tempore/passionis/ad-vesperas/hymnus'
    # XXX: The Eastertide psalter bits live at a different place from those for
    # Lent.  There are reasons why this is so, but not necessarily good ones:
    # the latter use the extra_keys mechanism.
    elif key == 'Pasch Versum 3':
        out_key = 'psalterium/pasc/ad-vesperas/versiculum'
    elif key == 'Hymnus Pasch Vespera':
        out_key = 'psalterium/pasc/ad-vesperas/hymnus'
    elif re.match(r'Day\d Versum [23]$', key):
        day = int(key[3])
        hour = 'vesperas' if key.endswith('3') else 'laudes'
        out_key = f'psalterium/{util.day_ids[day]}/ad-{hour}/versiculum'
    elif key == 'Day02 Versum 2':
        # Sundays in Septuagesimatide.
        out_key = f'psalterium/{util.day_ids[0]}/ad-laudes-ii/versiculum'
    elif key == 'Gloria':
        out_key = 'versiculi/gloria-patri-post-psalmum'
    elif key == 'Requiem':
        out_key = 'versiculi/requiem-aeternam-post-psalmum'
    elif key in versicle_keys or any(entry in post_process_keys
                                     for entry in [key, (do_basename, key)]):
        basename = key.replace(' ', '-').lower()
        prefix = 'versiculi' if key in versicle_keys else 'post-process'
        out_key = '%s/%s' % (prefix, basename,)
    elif key == 'Name':
        # St Valentine happens to be in the genitive, although I don't think
        # DO used it.  XXX: Merge this into name_case().
        out_key = ('nomen/genitivo' if do_basename.endswith('02-14')
                   else 'nomen/vocativo')
    elif do_basename.endswith('Doxologies'):
        name = {
            'Nat': 'nativitatis',
            'Epi': 'epiphaniae',
            'Pasc': 'paschalis',
            'Asc': 'ascensionis',
            'Pent': 'pentecostes',
        }.get(key, key)
        out_key = 'doxologiae/' + name
    elif key.startswith == 'Preces feriales Laudes':
        out_key = 'ordinarium/ad-laudes/preces-feriales'
    elif key.startswith == 'Preces feriales Vesperas':
        out_key = 'ordinarium/ad-vesperas/preces-feriales'
    else:
        if not key in warn_keys:
            print("WARNING: Unrecognised key %s" % (key,), file=sys.stderr)
            warn_keys[key] = None
        out_key = key.lower().replace(' ', '-')
    return out_key


def make_full_path(out_key_base, out_key):
    assert out_key or out_key_base
    components = []
    if out_key_base is not None:
        components.append(out_key_base)
    if out_key is not None:
        components.append(out_key)
    return '/'.join(components)



do_range_to_officium_psalm = {
    range(1, 93): lambda number: 'psalmi/%d' % (number,),
    range(95, 151): lambda number: 'psalmi/%d' % (number,),
    (231,): lambda number: 'ad-laudes/benedictus',
    (232,): lambda number: 'ad-vesperas/magnificat',
    (233,): lambda number: 'ad-completorium/nunc-dimittis',
    (234,): lambda number: 'ad-primam/symbolum-athanasium',
    # perl -Mutf8 -C -ne '
    #   if($ARGV =~ /Psalm23/) { close ARGV; next; }
    #   tr/áéíóúýǽÁÉÍÓÚÝǼ/aeiouyæœAEIOUYÆŒ/; s/æ/ae/g; s/œ/oe/g;
    #   s/[^\p{XPosixAlpha}*\d]+/-/g;
    #   if($. == 1) {
    #     ($title) = /Canticum-(.*?)-[*]/;
    #   }
    #   else {
    #     @words = /(\p{XPosixAlpha}+)/g;
    #     $incipit = "$words[0]-$words[1]";
    #     $incipit .= "-$words[2]" if $words[1] =~ /^(in|qui|cum|tu)$/;
    #     ($num) = $ARGV =~ /(2\d\d)/;
    #     print lc("($num,): lambda number: '"'"'cantici/$title-$incipit'"'"',\n");
    #     close ARGV;
    #   }' web/www/horas/Latin/psalms1/Psalm2??.txt
    (210,): lambda number: 'cantici/trium-puerorum-benedicite-omnia',
    (211,): lambda number: 'cantici/david-benedictus-es',
    (212,): lambda number: 'cantici/tobiae-magnus-es',
    (213,): lambda number: 'cantici/judith-hymnum-cantemus',
    (214,): lambda number: 'cantici/jeremiae-audite-verbum',
    (215,): lambda number: 'cantici/isaiae-vere-tu-es',
    (216,): lambda number: 'cantici/ecclesiastici-miserere-nostri',
    (220,): lambda number: 'cantici/trium-puerorum-benedictus-es',
    (221,): lambda number: 'cantici/isaiae-confitebor-tibi',
    (222,): lambda number: 'cantici/ezechiae-ego-dixi',
    (223,): lambda number: 'cantici/annae-exsultavit-cor',
    (224,): lambda number: 'cantici/moysis-cantemus-domino',
    (225,): lambda number: 'cantici/habacuc-domine-audivi',
    (226,): lambda number: 'cantici/moysis-audite-caeli',
    (240,): lambda number: 'cantici/isaiae-ecce-dominus',
    (241,): lambda number: 'cantici/isaiae-cantate-domino',
    (242,): lambda number: 'cantici/isaiae-haec-dicit',
    (243,): lambda number: 'cantici/isaiae-quis-est',
    (244,): lambda number: 'cantici/osee-in-tribulatione',
    (245,): lambda number: 'cantici/sophonee-quapropter-exspecta',
    (246,): lambda number: 'cantici/habacuc-oratio-habacuc',
    (247,): lambda number: 'cantici/habacuc-pro-iniquitate',
    (248,): lambda number: 'cantici/habacuc-egressus-es',
    (249,): lambda number: 'cantici/ecclesiasticae-obaudite-me',
    (250,): lambda number: 'cantici/isaiae-gaudens-gaudebo',
    (251,): lambda number: 'cantici/isaiae-non-vocaberis',
    (253,): lambda number: 'cantici/isaiae-vos-autem',
    (254,): lambda number: 'cantici/sapientiae-fulgebunt-justi',
    (255,): lambda number: 'cantici/sapientiae-reddidit-deus',
    (256,): lambda number: 'cantici/ecclesiasticae-beatus-vir',
    (257,): lambda number: 'cantici/jeremiae-benedictus-vir',
    (258,): lambda number: 'cantici/ecclesiaticae-beatus-dives',
    (259,): lambda number: 'cantici/sapientiae-justorum-autem',
    (260,): lambda number: 'cantici/tobiae-benedicite-dominum',
    (261,): lambda number: 'cantici/isaiae-et-erit',
    (262,): lambda number: 'cantici/jeremiae-sta-in-porta',
    (263,): lambda number: 'cantici/isaiae-populus-qui-ambulabat',
    (264,): lambda number: 'cantici/isaiae-urbs-fortitudinis',
    (265,): lambda number: 'cantici/isaiae-laetamini-cum-jerusalem',
    (266,): lambda number: 'cantici/isaiae-domine-miserere',
    (267,): lambda number: 'cantici/isaiae-audite-qui-longe',
    (268,): lambda number: 'cantici/ecclesiasticae-miserere-plebi',
}
do_to_officium_psalm = {
    do_psalm_no: func(do_psalm_no)
    for (do_psalm_range, func) in do_range_to_officium_psalm.items()
    for do_psalm_no in do_psalm_range
}

def name_case(do_basename, do_key):
    if do_basename.endswith('C1'):
        return 'nominativo'
    if do_basename.endswith('C1v') and do_key == 'Oratio':
        return 'nominativo'
    if do_basename.endswith('C2') and do_key == 'Oratio3':
        return 'ablativo'
    if do_basename.endswith('Major Special') and do_key.startswith('Suffragium'):
        return 'ablativo'
    if do_basename.endswith('C4') and re.match(r'Oratio[29]', do_key):
        # This includes Oratio91.
        return 'accusativo'
    if any(do_basename.endswith(x)
           for x in ['C4a', 'C4ap']) and do_key == 'Ant 1':
        return 'vocativo'
    if do_basename.endswith('C4ap') and do_key == 'Oratio2':
        return 'accusativo'
    if do_basename.endswith('C6') and do_key == 'Oratio1':
        return 'nominativo'
    if do_basename.endswith('SanctiM/C7') and do_key == 'Responsory9':
        return 'nominativo'
    return 'genitivo'


def apply_subs_to_str(subs, thing):
    subbed = False
    for pat, repl in re.findall(r's/([^/]*?)/([^/]*?)/', subs or ''):
        try:
            thing = re.sub(pat, repl, thing)
        except re.error:
            continue
        subbed = True
    if subs and not subbed:
        print("WARNING: failed to parse substitution", subs, file=sys.stderr)
    return thing


inclusion_regex = r'@([^:]*)(?::([^:]*))?(?::([^:]*))?'
def apply_inclusion(line, do_propers_base, do_basename, do_key, do_rubric_name,
                    options):
    try:
        basename, key, subs = re.match(inclusion_regex, line).groups()
        basename = basename or do_basename
        key = key or do_key
        do_propers = load_do_file(do_propers_base, do_rubric_name, options,
                                  basename)
        included = do_propers[key]
    except (AttributeError, FileNotFoundError, KeyError):
        yield line
        return

    m = re.match(r'(\d+)(?:-(\d+))?$', subs or '')
    if m:
        # Line-range.
        start, stop = m.groups()
        stop = stop or start
        included = included[int(start) - 1:int(stop)]
        subs = None

    for included_line in included:
        if re.match(inclusion_regex, included_line):
            sublines = apply_inclusion(included_line, do_propers_base,
                                       basename, key, do_rubric_name, options)
        else:
            sublines = [included_line]
        for subline in sublines:
            yield apply_subs_to_str(subs, subline)


def do_to_officium_psalm_spec(do_psalm_spec):
    """Map <do_psalm_no>(<range>) to <officium_psalm_spec>(<range>)."""
    try:
        range_start = do_psalm_spec.index('(')
        do_psalm_no, range_spec = (do_psalm_spec[:range_start],
                                   do_psalm_spec[range_start:])
    except ValueError:
        do_psalm_no = do_psalm_spec
        range_spec = None

    officium_psalm_spec = do_to_officium_psalm[int(do_psalm_no)]
    if range_spec is not None:
        officium_psalm_spec += range_spec
    return officium_psalm_spec

def merge_do_section_to_path(propers, generic, do_basename, do_key, value,
                             out_path):
    template_var = 'officium.nomen_'
    if do_key.startswith('Suffragium'):
        template_var += 'titularis_'
    template_var += name_case(do_basename, do_key)

    # XXX: Latin-specific.
    value = [
        re.sub(r'\bN[.] et N[.]\B',
               '{{%s[0]}} et {{%s[1]}}' % (template_var, template_var),
               x)
        for x in value
    ]
    value = [re.sub(r'\bN[.]\B', '{{%s}}' % (template_var,), x)
             for x in value]
    # XXX: Doing this unconditionally is a bit rash.
    value = [re.sub(r'^[VR]\. ', '', line) for line in value]

    if out_path.endswith('/antiphonae'):
        # Separate out the psalms.
        try:
            value, psalms = zip(*(entry.rstrip(';;').split(';;')
                                  for entry in value))
        except ValueError:
            # Some or all entries were missing psalms.
            pass
        else:
            generic[out_path[:-len('/antiphonae')] + '/psalmi'] = [
                [do_to_officium_psalm_spec(p) for p in psalm_spec.split(';')]
                for psalm_spec in psalms
            ]
            value = list(value)
            if not any(value):
                # No antiphons, only psalms.  Nothing more to do.
                return
    elif out_path.endswith('/hymnus'):
        verse = []
        verses = [verse]
        variable_doxology = False
        for line in value:
            if line.strip() == '_':
                verse = []
                verses.append(verse)
            else:
                line = re.sub(r'^([{].*[}])?(v[.]\s*)?', '', line)
                if line.startswith('*'):
                    line = re.sub(r'^[*]\s*', '', line)
                    variable_doxology = True
                verse.append(line)
        if variable_doxology:
            value = {
                'type': 'hymnus-cum-doxologia-mutabile',
                'content': verses,
            }
        else:
            value = verses
    elif out_path.endswith('/haec-dies'):
        value = [re.sub(r'^Ant\. |[*]\s*', '', x) for x in value]
    elif 'capitulum' in out_path:
        if value and value[0].startswith('!'):
            value = {
                'scripture_ref': re.sub(r'^!\s*', '', value[0]),
                'content': value[1:]
            }
    elif '/nomen/' in out_path and len(value) == 1:
        value = value[0]
    propers[out_path] = value



def merge_do_section(propers, redirections, do_redirections, generic, options,
                     do_propers_base, do_rubric_name, do_basename,
                     out_key_base, do_key, value, extra_rubrics, calpoint,
                     calendar_descs):
    if do_key == 'Rank':
        m = re.search(r'\b(ex|vide)\b\s+\b(.*)\b\s*$', value[0])
        if m:
            assert out_key_base
            basename = m.group(2)
            if re.match(r'C\d+', basename):
                out_key_common = make_full_path(out_key_base, 'commune')
                redirections[out_key_common] = 'commune/' + basename
                # Use the -p variant for Easter.  These don't always exist, but
                # those cases will get dropped cleanly in due course.
                easter_common_out_key = make_full_path(out_key_common, 'pasc')
                redirections[easter_common_out_key] = 'commune/%sp' % (basename,)
                if m.group(1) == 'ex':
                    dict_list_append(extra_rubrics, out_key_base,
                                     'omnia de communi')
            else:
                if '/' not in basename:
                    if re.match(r'\d\d-\d\d', basename):
                        basename = 'Sancti/' + basename
                    else:
                        basename = 'Tempora/' + basename
                do_redirections[out_key_base] = (basename, None)
    elif do_key == 'Rule':
        for line in value:
            m = re.match(r'[OC]Papae?[MCD]=(.*);', line)
            if m:
                out_path = make_full_path(out_key_base, 'nomen/accusativo')
                # We might have one name, or we might have two.
                raw_names = m.group(1)
                m = re.match(r'(.*) et (.*)$', raw_names)
                names = list(m.groups()) if m else raw_names
                propers[out_path] = names
            elif line.casefold() == 'preces feriales':
                dict_list_append(extra_rubrics, out_key_base, 'preces feriales')
    elif do_key.startswith('Commemoratio'):
        if do_key == 'Commemoratio4':
            # St Peter or St Paul.
            print("WARNING: TODO: Commemoratio4", do_basename, file=sys.stderr)
            return
        elif do_key == 'Commemoratio 5':
            # This is used exactly once, to handle commemoration of the octave
            # day of All Saints in first Vespers of the Dedication of the
            # Lateran Basilica.  officium gets this right without having to
            # special-case it like this, so just ignore it.
            assert do_basename == 'Sancti/11-09'
            return
        elif not calendar_descs or not calendar_descs[1:]:
            # Must have been referenced from an inclusion.
            print(f"WARNING: Don't know where to put commemorations for {do_basename}",
                  file=sys.stderr)
            return

        suffixes = {
            1: '/ad-i-vesperas',
            2: '/ad-laudes',
            3: '/ad-ii-vesperas',
        }
        commem_offices = [
            desc for desc in calendar_descs[1:]
            if not issubclass(calendar.CalendarResolver.descriptor_class(desc),
                              offices.Vigil)
        ]
        commems = list(parse_commemorations(value))
        m = re.search(r'(\d)$', do_key)
        digit = m and int(m.group(1))
        if len(commem_offices) > len(commems) and digit == 1:
            # Hmm.  More offices than commemorations at first Vespers, so one
            # of the offices doesn't get first Vespers.  DO's commemoration
            # semantics are such that this only happens when one of the
            # commemorated offices is a day within an octave and the office of
            # the preceding day is of the octave.  Filter it out.
            commem_offices = [
                desc for desc in commem_offices
                if not issubclass(calendar.CalendarResolver.descriptor_class(desc),
                                  offices.WithinOctave)
            ]
        if len(commem_offices) < len(commems):
            # E.g. 10-07r, where a whole-file inclusion pulls in a Divino
            # commemoration that gets squashed by 1960 commem-limit logic.
            print(f"WARNING: Too many commemorations for {do_basename}:{do_key}",
                  file=sys.stderr)
        if len(commem_offices) > len(commems) and do_basename != 'Sancti/07-01':
            # Too few commemorations.  The 07-01 exception is for the day
            # within the octave of Ss. Peter and Paul, which is not
            # commemorated on that day.
            assert False, (commem_offices, commems)
        for calentry, com in zip(commem_offices, commems):
            base_path = make_proper_path(calentry, calpoint)

            have_redirect = False
            digit_recurse = False
            while 'do-ref-basename' in com:
                # TODO: Actually handle Gregem.
                if (com['do-ref-key'] is None or
                    re.match(r'Oratio\d?(\s+(proper|Gregem|proper Gregem))?',
                             com['do-ref-key'])):
                    com['do-ref-key'] = None
                    have_redirect = True
                    break
                else:
                    expanded = apply_inclusion(com['do-ref-raw'],
                                               do_propers_base, do_basename,
                                               do_key, do_rubric_name, options)
                    expanded = list(expanded)
                    if expanded[0].startswith('@'):
                        # The inclusion failed, but maybe it was an implicit-
                        # digit case (like Octava meaning Octava [123]).
                        # XXX: This code is badly broken and can recurse
                        # infinitely.  Why are we recursing at all?  Just give
                        # up for now.
                        return
                        for add_digit in [digit] if digit else suffixes:
                            digitised_key = (do_key if digit else
                                             f'{do_key} {add_digit}')
                            digitised_value = [f'{expanded[0]} {add_digit}']
                            if 'oratio' in com:
                                digitised_value += ['$Oremus', com['oratio']]
                            merge_do_section(propers, redirections,
                                             do_redirections, generic, options,
                                             do_propers_base, do_rubric_name,
                                             do_basename, out_key_base,
                                             digitised_key, digitised_value,
                                             extra_rubrics, calpoint,
                                             calendar_descs)
                        digit_recurse = True
                        break
                    else:
                        (com,) = parse_commemorations(expanded)
            else:
                # We assume that redirections only occur in the first lines of
                # commemorations.
                assert all('@' not in v for v in com.values())

            if digit_recurse:
                # We handled this commemoration in the recursions.
                continue

            if have_redirect:
                if digit is not None and com['do-ref-key'] is not None:
                    com_redirs = {
                        base_path + suffixes[digit]:
                        (com['do-ref-basename'],
                         # TODO: Is it always safe to append the digit?  Can do-ref-key be something like Oratio proper?  Yes, it can, and so it's not safe; and moreover, what if do-ref-key is not a thing that should have a digit applied?  I think DO would try the digitised version first, and then fall back.
                         f"{com['do-ref-key']} {digit}")
                    }
                else:
                    com_redirs = {
                        base_path: (com['do-ref-basename'], com['do-ref-key'])
                    }
                do_redirections.update(com_redirs)
            prefix = base_path + (suffixes[digit] if digit is not None else '')
            for proper_path, proper_text in commemoration_propers(com):
                propers[prefix + '/' + proper_path] = proper_text
    elif do_key == 'Oratio Vigilia':
        # TODO: Do this.
        print("WARNING: TODO: Oratio Vigilia", do_basename, file=sys.stderr)
        return
        calentry, = vigils
        propers[path(calentry) + '/oratio'] = proper_text
    else:
        out_path = make_full_path(out_key_base, make_out_key(do_key,
                                                             do_basename))
        # Handle inclusions.  We treat single-line values specially: if these
        # contain an inclusion, we set up an indirect reference to resolve that
        # inclusion, rather than expanding it inline.
        if len(value) == 1:
            m = re.match(inclusion_regex, value[0])
        else:
            value = [x
                     for mapped in (apply_inclusion(line, do_propers_base,
                                                    do_basename, do_key,
                                                    do_rubric_name, options)
                                    for line in value)
                     for x in mapped]
            m = None
        if m:
            redir_basename, redir_key, subs = m.groups()
            if not redir_basename:
                redir_basename = do_basename
            if not redir_key:
                redir_key = do_key

            sub_list = []
            for sub in re.findall(r's/[^/]*?/[^/]*?/', subs or ''):
                names = None
                m = re.match(r's/N\\\. et N\\\./([^/]*)', sub)
                if m:
                    # If we have two names, store an array of them.
                    names = m.group(1).split(' et ')
                m = not names and re.match(r's/N\\\./([^/]*)', sub)
                if m:
                    # With one name, just store a string.
                    names = m.group(1)
                if names is not None:
                    case = name_case(redir_basename, redir_key)
                    sub_out_path = make_full_path(out_key_base,
                                                  'nomen/%s' % (case,))
                    propers[sub_out_path] = names
                else:
                    sub_list.append(sub)

            assert 'post-process' not in out_path
            if sub_list:
                # We have unhandled substitutions, so expand the inclusion
                # now.
                value = list(apply_inclusion(value[0], do_propers_base,
                                             do_basename, do_key,
                                             do_rubric_name, options))
                propers[out_path] = value
            else:
                do_redirections[out_path] = (redir_basename, redir_key)
        else:
            merge_do_section_to_path(propers, generic, do_basename, do_key,
                                     value, out_path)

def load_do_file(do_propers_base, do_rubric_name, options, do_basename):
    assert do_basename
    do_filename = os.path.join(do_propers_base, do_basename + '.txt')
    try:
        do_propers = parse(do_filename, options, do_rubric_name)
    except FileNotFoundError:
        print("Not found: %s" % (do_filename,), file=sys.stderr)
        raise
    return do_propers


def merge_do_propers(propers, redirections, do_redirections, generic,
                     do_propers_base, do_basename, out_key_base, options,
                     do_rubric_name, extra_rubrics, calpoint, calendar_descs):
    try:
        do_propers = load_do_file(do_propers_base, do_rubric_name, options,
                                  do_basename)
    except FileNotFoundError:
        return False
    for (do_key, value) in do_propers.items():
        merge_do_section(propers, redirections, do_redirections, generic,
                         options, do_propers_base, do_rubric_name, do_basename,
                         out_key_base, do_key, value, extra_rubrics, calpoint,
                         calendar_descs)
    return True


def parse_commemorations(lines):
    lines_iter = iter(lines)
    for first_line in lines_iter:
        commem = {}
        try:
            while first_line.startswith('!'):
                first_line = next(lines_iter)
            # If the _first_ line is an @-ref, then it's a special inclusion
            # for commemorations.  @-refs elsewhere are left for expansion by
            # the usual mechanism.
            m = re.match(inclusion_regex, first_line)
            if m:
                # Parse the inclusion.
                basename, key, subs = m.groups()
                commem['do-ref-basename'] = basename
                commem['do-ref-key'] = key
                commem['do-ref-subs'] = subs
                commem['do-ref-raw'] = first_line
                # Maybe fall through to parsing a prayer, but if the next line
                # is _, the prayers comes from the inclusion and this
                # commemoration is complete.
                next_line = next(lines_iter)
                if next_line == '_':
                    # End of this commemoration.  The "finally" block will
                    # yield it, and then we'll move on to the next one.
                    continue
            else:
                # Parse antiphon and versicle.
                commem['antiphona'] = [first_line]
                assert next(lines_iter) == '_'
                versicle = next(lines_iter)
                response = next(lines_iter)
                commem['versiculum'] = [versicle, response]
                assert next(lines_iter) == '_'
                next_line = next(lines_iter)

            # XXX: Hideous hack: There's an occurrence of
            #   @Something
            #   (sed tempore paschali) @Something_else
            # but we don't handle inline conditionals.  Just detect it and
            # skip it.
            if next_line.startswith('('):
                print(f"WARNING: Ignoring conditional in {next_line}",
                      file=sys.stderr)
                next_line = next(lines_iter)

            # Parse the prayer.
            assert next_line.startswith('$Oremus')
            prayer = next(lines_iter)
            conclusion = next(lines_iter)
            try:
                if conclusion == '_':
                    # This is the case where we're in a non-final
                    # commemoration, and DO simply omitted the conclusion of
                    # the collect in the datafile.  Ho hum.  Let's just guess
                    # that it's Per Dominum.  TODO: Check all of these.
                    print(f"WARNING: Guessing conclusion in {commem} for {prayer}",
                          file=sys.stderr)
                    conclusion = '$Per Dominum'
                else:
                    # If we have a next line, it must be '_' as a separator
                    # between multiple commemorations.  If we don't have a next
                    # line, we'll fall into the outer "except" block.
                    assert next(lines_iter) == '_'
            finally:
                commem['oratio'] = [prayer, conclusion]
        except StopIteration:
            # This branch catches the case where we run out of lines in the
            # middle of parsing a commemoration.  This is not necessarily
            # unexpected: in particular, this is how we handle @-ref
            # commemorations without overridden prayers and with no following
            # commemorations.
            pass
        finally:
            assert commem
            yield commem


def commemoration_propers(commem):
    for part in ['antiphona', 'versiculum', 'oratio']:
        if part in commem:
            yield (part, commem[part])


triduum_days = [
    'feria-quinta-in-cena-domini',
    'feria-sexta-in-parasceve',
    'feria-sexta-in-passione-et-morte-domini',
    'sabbato-sancto',
]
def post_process(propers, key):
    if 'post-process' in key:
        # XXX: This is nasty.  "post-process/" occurs between the base (i.e.
        # the bit that came from the DO filename) and the translated key.
        name = re.sub(r'post-process/', '', key)
    else:
        name = key
    val = propers[key]

    if name == 'dominus':
        propers['versiculi/dominus-vobiscum'] = val[:2]
        propers['versiculi/domine-exaudi'] = val[2:4]
    elif name == 'benedicamus-domino':
        propers['versiculi/benedicamus-domino'] = val[0]
        propers['versiculi/deo-gratias'] = val[1]
    elif name == 'fidelium-animae':
        propers['versiculi/fidelium-animae'] = val[0]
        propers['versiculi/amen'] = val[1]
    elif name == 'pater_noster1':
        propers['orationes/pater-noster-secreto'] = [val[0]]
        propers['orationes/et-ne-nos-inducas'] = val[1:]
    elif name == 'commune/C9/oratio-21':
        propers['officium-defunctorum/preces'] = val[3:7]
    elif name == 'commune/C9/conclusio':
        propers['versiculi/requiem'] = val[:2]
        propers['versiculi/requiescant'] = val[2:]
    elif name == 'commune/C9/oratio_fid':
        # We're overriding the prayer here, as the one specified by DO consists
        # of two @-refs, which we can't handle.  Check that it is in fact there
        # already, so we don't clobber it later.  And: XXX: This is completely
        # spurious.
        new_key = 'commune/C9/oratio_a_porta'
        assert new_key in propers
        propers[new_key] = val[-2:]
    elif name in [
        'per-dominum',
        'per-eundem',
        'qui-vivis',
        'qui-tecum',
        'per-dominum-eiusdem',
        'qui-tecum-eiusdem',
    ]:
        # XXX: Should put these somewhere other than the root.
        propers[name] = val[0]
    elif any(name.endswith('%s/oratio' % (day,)) for day in triduum_days):
        propers[name] = val[-3:]
        propers[re.sub(r'oratio$', 'christus-factus-est', name)] = val[:1]
    elif name == 'ordinarium/ad-vesperas/preces-feriales':
        # Trim Kyrie and Pater from beginning, and Domine exaudi from end.
        propers[name] = val[2:-2]
        propers['ordinarium/kyrie-simplex'] = val[0]
    elif name in ['suffragium%s' % (k,) for k in suffrage_map]:
        base = 'suffragia/' + suffrage_map[name[len('suffragium'):]]
        for part in ['ad-canticum', 'versiculum']:
            entry = propers['%s/%s' % (base, part)] = []
            while val:
                item = val.pop(0)
                if item.strip() == '_':
                    break
                entry.append(item)
        entry = propers['%s/oratio' % (base,)] = val[-2:]

    if name != key:
        del propers[key]


def make_proper_path(desc, calpoint):
    return 'proprium/%s' % (desc.get('titulus', calpoint),)


def propers(calendar_data, options, do_rubric_name):
    propers = {}
    generic = {}
    redirections = {}
    do_redirections = {}
    do_filename_to_officium = {}
    extra_rubrics = {}

    do_propers_base = os.path.join(options.do_basedir, 'web', 'www', 'horas',
                                   options.language)

    def merge():
        do_filename_to_officium[do_basename] = out_key_base
        return merge_do_propers(propers, redirections, do_redirections, generic,
                                do_propers_base, do_basename, out_key_base,
                                options, do_rubric_name, extra_rubrics,
                                calpoint, calendar_descs)

    for (entry, calendar_descs) in calendar_data.dictionary.items():
        if not entry.startswith('calendarium/'):
            continue
        calpoint = entry[len('calendarium/'):]
        do_basename = make_do_basename(calpoint)
        out_key_base = make_proper_path(calendar_descs[0], calpoint)
        merge()

    # These are referenced by merge(), but they're only meaningful in the above
    # loop.  Reset them so that we catch any subsequent accidental accesses.
    calendar_descs = calpoint = None

    # August-November weeks.
    for day in ('%02d%d-%d' % x
                for x in itertools.product(range(8, 12), range(1, 6),
                                           range(0, 7))):
        do_basename = os.path.join('Tempora', day)
        out_key_base = 'proprium/%s' % (day,)
        merge()

    for common in (key[8:] for key in redirections.values()
                   if key.startswith('commune/')):
        do_basename = os.path.join('Commune', common)
        out_key_base = 'commune/%s' % (common,)
        merge()

    out_key_base = None
    for basename in ["Psalmi major", "Major Special", "Prayers", "Doxologies"]:
        do_basename = os.path.join('Psalterium', basename)
        merge()

    for psalm in do_to_officium_psalm:
        with open(os.path.join(do_propers_base, 'psalms1',
                               'Psalm%d.txt' % (psalm,))) as f:
            raw = [line.strip() for line in f.readlines()]
        propers['psalterium/' + do_to_officium_psalm[psalm]] = raw

    # The triple "alleluia" antiphon used in Divino and later is synthesised
    # in DO, but it happens to be the same as the antiphon on the Laudate
    # psalms in the pre-Divino psalter.
    propers['psalterium/pasc/ad-vesperas/antiphonae'] = propers['daymp-laudes'][-1].split(';;')[0]

    for key in list(propers.keys()):
        post_process(propers, key)

    # We omit "Per Dominum" here, because that's the default.
    known_conclusions = {
        'per eundem',
        'qui vivis',
        'qui tecum',
        'per dominum eiusdem',
        'qui tecum eiusdem',
    }
    generic['conclusions'] = {}
    for key, value in propers.items():
        if value and isinstance(value, list) and isinstance(value[-1], str) and value[-1].startswith('$'):
            ref = value.pop()[1:].strip().lower().replace('j', 'i').replace('eumdem', 'eundem')
            if ref in known_conclusions:
                generic['conclusions'][key] = ref.replace(' ', '-')

    converted_redirections = {}
    warn_do_filenames = {}
    def make_officium_redir(do_basename, do_key):
        if do_basename not in do_filename_to_officium:
            if do_basename not in warn_do_filenames:
                warn_do_filenames[do_basename] = None
                print("WARNING: discarding redirection to", do_basename,
                      file=sys.stderr)
            return None
        return make_full_path(do_filename_to_officium[do_basename],
                              make_out_key(do_key, do_basename))

    while do_redirections:
        remaining_redirections = {}
        for (redir_key, (do_basename, do_key)) in do_redirections.items():
            dest = make_officium_redir(do_basename, do_key)
            if dest is not None:
                converted_redirections[redir_key] = dest
                if all(x.endswith('/antiphonae') for x in [dest, redir_key]):
                    psalm_redir_key = redir_key[:-len('antiphonae')] + 'psalmi'
                    psalm_dest = dest[:-len('antiphonae')] + 'psalmi'
                    converted_redirections[psalm_redir_key] = psalm_dest
            else:
                remaining_redirections[redir_key] = (do_basename, do_key)

        do_redirections = dict(remaining_redirections)
        for (redir_key, (do_basename, do_key)) in remaining_redirections.items():
            out_key_base = '/'.join(['do_xref', do_basename])
            if not merge():
                del do_redirections[redir_key]

    return (
        generic,
        propers,
        redirections,
        converted_redirections,
        extra_rubrics,
    )


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--do-basedir', default='.')
    parser.add_argument('--format', choices=[
                            'raw',
                            'propers',
                            'generic',
                        ],
                        default='generic')
    # This is used as the subdirectory of web/www/horas.
    parser.add_argument('--language', choices=[
                            'Latin',
                            'English',
                        ],
                        default='Latin')
    parser.add_argument('--rubrics', '-r', choices=do_rubric_names.keys(),
                        default='rubricarum')
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('calcalc_calendar_datafile')
    return parser.parse_args()


def main(options):
    do_rubric_name = do_rubric_names[options.rubrics]
    calcalc = parse(options.calcalc_calendar_datafile, options, do_rubric_name)

    if options.format != 'raw':
        cal_raw = make_calendar(calcalc, do_rubric_name)
        calendar = bringup.make_generic(options.rubrics, cal_raw)
        (
            generic,
            propers_data,
            redirections,
            converted_redirections,
            extra_rubrics,
        ) = propers(calendar, options, do_rubric_name)

        if options.format == 'propers':
            out = [['create', propers_data]]
            if redirections:
                out.append(['redirect', redirections])
            if converted_redirections:
                out.append(['redirect', converted_redirections])
        else:
            assert options.format == 'generic'

            # Add stuff to the office descriptors that was scraped from the
            # per-language DO files.  We have no indexing into the descriptors,
            # so we just iterate over the whole lot.
            for record in cal_raw:
                for calpoint, descs in record[1].items():
                    for desc in descs:
                        proper_path = make_proper_path(desc, calpoint)
                        if proper_path in extra_rubrics:
                            for rubric in extra_rubrics[proper_path]:
                                add_rubric(desc, rubric)

            out = cal_raw + [['create', generic]]
    else:
        out = calcalc

    print(yaml.dump(out, allow_unicode=True, Dumper=yaml.CDumper))


if __name__ == '__main__':
    main(parse_args())
