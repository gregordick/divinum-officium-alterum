#!/usr/bin/python3

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
from officium import util


def do_rubric_expression_matches(expression, do_rubric_name):
    return do_rubric_name.lower() in expression.lower()


def add_rubric(desc, rubric):
    rubrics = desc.setdefault('rubricae', [])
    rubrics.append(rubric)


def terminatur_post_nonam(desc):
    add_rubric(desc, 'officium terminatur post nonam')


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
        elif remaining_line == 'Officium terminatur post Nonam':
            terminatur_post_nonam(desc)

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

def _parse(f, options, do_rubric_name):
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
                if section and cond_matches:
                    section.pop()
            elif 'omittuntur' in line:
                # XXX: Should only clobber as far back as the beginning of the
                # block.
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

        m = re.match(r'\[(.*)\].*' + do_rubric_name, line)
        if not m:
            m = re.match(r'\[(.*)\]$', line)
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

        if line.startswith(('V. ', 'R. ', 'v. ', 'r. ')):
            line = line[3:]

        if not rubric_squashed and section is not None:
            section.append(line)

    # Trim trailing blank lines.
    for section in raw:
        while raw[section] and not raw[section][-1]:
            raw[section].pop()

    return raw


def parse(filename, options, do_rubric_name):
    with open(filename, 'r') as f:
        return _parse(f, options, do_rubric_name)


def make_calendar(raw, do_rubric_name):
    d = {
        'calendarium/' + k: list(make_descriptors('calendarium/' + k, v,
                                                  do_rubric_name))
        for (k, v) in expand_calendar_at_refs(raw).items()
    }

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
    ]
    if key is None:
        return None
    elif key == 'Ant 1':
        out_key = 'ad-i-vesperas/ad-magnificat'
    elif key == 'Ant 3':
        out_key = 'ad-ii-vesperas/ad-magnificat'
    elif key.startswith('Ant Vespera'):
        if key == 'Ant Vespera 1':
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
    elif re.match(r'Day\d Vespera$', key):
        day = int(key[3])
        # This key is either the chapter or the antiphons and psalms, depending
        # on which file it came from.
        part = ('capitulum' if do_basename.endswith('Major Special')
                else 'antiphonae')
        out_key = 'psalterium/%s/ad-vesperas/%s' % (util.day_ids[day], part)
    elif re.match(r'Hymnus Day\d Vespera$', key):
        day = int(key[10])
        out_key = 'psalterium/%s/ad-vesperas/hymnus' % (util.day_ids[day],)
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
    elif re.match(r'Day\d Versum 3$', key):
        day = int(key[3])
        out_key = 'psalterium/%s/ad-vesperas/versiculum' % (util.day_ids[day],)
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



do_to_officium_psalm = {
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


def name_case(do_basename, do_key):
    if do_basename.endswith('C1'):
        return 'nominativo'
    if do_basename.endswith('C1v') and do_key == 'Oratio':
        return 'nominativo'
    if do_basename.endswith('C2') and do_key == 'Oratio3':
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
        key = key or do_key
        do_propers = load_do_file(do_propers_base, do_rubric_name, options,
                                  basename or do_basename)
        included = do_propers[key]
    except (AttributeError, FileNotFoundError, KeyError):
        yield line
        return
    for included_line in included:
        if re.match(inclusion_regex, included_line):
            sublines = apply_inclusion(included_line, do_propers_base,
                                       basename, key, do_rubric_name, options)
        else:
            sublines = [included_line]
        m = re.match(r'(\d+)(?:-(\d+))?$', subs or '')
        if m:
            # Line-range.
            start, stop = m.groups()
            stop = stop or start
            for subline in itertools.islice(sublines, int(start),
                                            int(stop) + 1):
                yield subline
        else:
            # Substitutions.
            for subline in sublines:
                yield apply_subs_to_str(subs, subline)


def merge_do_section(propers, redirections, do_redirections, generic, options,
                     do_propers_base, do_rubric_name, do_basename,
                     out_key_base, do_key, value):
    if do_key == 'Rank':
        m = re.search(r'\b(ex|vide)\b\s+\b(.*)\b\s*$', value[0])
        if m:
            # TODO: Distinguish between "ex" and "vide".
            assert out_key_base
            basename = m.group(2)
            if re.match(r'C\d+', basename):
                out_key_common = make_full_path(out_key_base, 'commune')
                redirections[out_key_common] = 'commune/' + basename
                # Use the -p variant for Easter.  These don't always exist, but
                # those cases will get dropped cleanly in due course.
                easter_common_out_key = make_full_path(out_key_common, 'pasc')
                redirections[easter_common_out_key] = 'commune/%sp' % (basename,)
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
            template_var = 'officium.nomen_' + name_case(do_basename, do_key)
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
                    value, psalms = zip(*(entry.split(';;')
                                          for entry in value))
                    generic[out_path[:-len('/antiphonae')] + '/psalmi'] = [
                        ['psalmi/%s' % (p,) for p in psalm_spec.split(';')]
                        for psalm_spec in psalms
                    ]
                    value = list(value)
                except ValueError:
                    # Some or all entries were missing psalms.
                    pass
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
                     do_rubric_name):
    try:
        do_propers = load_do_file(do_propers_base, do_rubric_name, options,
                                  do_basename)
    except FileNotFoundError:
        return False
    for (do_key, value) in do_propers.items():
        merge_do_section(propers, redirections, do_redirections, generic,
                         options, do_propers_base, do_rubric_name, do_basename,
                         out_key_base, do_key, value)
    return True


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

    if name != key:
        del propers[key]


def propers(calendar_data, options, do_rubric_name):
    propers = {}
    generic = {}
    redirections = {}
    do_redirections = {}
    do_filename_to_officium = {}

    do_propers_base = os.path.join(options.do_basedir, 'web', 'www', 'horas',
                                   options.language)

    def merge():
        do_filename_to_officium[do_basename] = out_key_base
        return merge_do_propers(propers, redirections, do_redirections, generic,
                                do_propers_base, do_basename, out_key_base,
                                options, do_rubric_name)

    for (entry, descs) in calendar_data.dictionary.items():
        if not entry.startswith('calendarium/'):
            continue
        calpoint = entry[len('calendarium/'):]
        do_calpoint = re.sub(r'Pent(\d)-', r'Pent0\1-', calpoint)
        do_basename = os.path.join(
            'Sancti' if re.match(r'\d\d-\d\d$', calpoint) else 'Tempora',
            do_calpoint,
        )
        # XXX: descs[0] is wrong.
        out_key_base = 'proprium/%s' % (descs[0].get('titulus', calpoint),)
        merge()

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

    for basename in ["Psalmi major", "Major Special", "Prayers", "Doxologies"]:
        do_basename = os.path.join('Psalterium', basename)
        out_key_base = None
        merge()

    for psalm_range in do_to_officium_psalm:
        for psalm in psalm_range:
            with open(os.path.join(do_propers_base, 'psalms1',
                                   'Psalm%d.txt' % (psalm,))) as f:
                raw = [line.strip() for line in f.readlines()]
            propers['psalterium/' + do_to_officium_psalm[psalm_range](psalm)] = raw

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

    if options.format == 'generic':
        return [['create', generic]]

    output = [['create', propers]]
    if redirections:
        output.append(['redirect', redirections])

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

    if converted_redirections:
        output.append(['redirect', converted_redirections])

    return output


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
    parser.add_argument('datafile')
    return parser.parse_args()


def main(options):
    do_rubric_name = do_rubric_names[options.rubrics]
    out = parse(options.datafile, options, do_rubric_name)

    if options.format != 'raw':
        out = make_calendar(out, do_rubric_name)
        from_propers = propers(bringup.make_generic(options.rubrics, out),
                               options, do_rubric_name)
        if options.format == 'propers':
            out = from_propers
        else:
            assert options.format == 'generic'
            out += from_propers

    print(yaml.dump(out, allow_unicode=True, Dumper=yaml.CDumper))


if __name__ == '__main__':
    main(parse_args())
