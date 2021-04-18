#!/usr/bin/python3

"""Script to generate bringup datafiles from protoype calcalc calendar and DO
datafiles.
"""

# XXX: Some of this is pretty unpleasant.

import argparse
import os
import re
import sys

import yaml

from officium import util

from officium import bringup


def make_descriptor(key, calcalc_lines):
    desc = {}
    if calcalc_lines and not calcalc_lines[0].startswith('rank='):
        desc['titulus'] = re.sub(r'\W+', '-', calcalc_lines.pop(0).lower())

    # Find the rankline.
    rankline = None
    while calcalc_lines:
        rankline = calcalc_lines.pop(0)
        if '(sed' not in rankline:
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

        if rankline.startswith('Festum'):
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

    return desc


def make_descriptors(key, calcalc_lines):
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
        elif lines:
            if not drop:
                yield make_descriptor(key, lines)
                yielded = True
            drop = False
            lines = []
    if lines or not yielded:
        yield make_descriptor(key, lines)


def _parse(f, options):
    raw = {}
    # Completely spurious parser, but good enough.
    rubric_squashed = False
    section = None
    accumulator = ''
    for line in f:
        line = line.rstrip()

        if line.endswith('~'):
            accumulator += line[:-1]
            continue

        if re.match(r'[(].*[)]$', line):
            rubric_squashed = '1960' not in line and 'deinde' not in line
            if rubric_squashed and options.verbose:
                print('SQUASH:', line, file=sys.stderr)
            continue

        m = re.match(r'\[(.*)\].*1960', line)
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

        if not rubric_squashed and section is not None and '=' not in line or line.startswith('rank='):
            section.append(line)

    # Trim trailing blank lines.
    for section in raw:
        while raw[section] and not raw[section][-1]:
            raw[section].pop()

    return raw


def parse(filename, options):
    with open(filename, 'r') as f:
        return _parse(f, options)


def calendar(raw):
    d = {
        'calendarium/' + k: list(make_descriptors('calendarium/' + k, v))
        for (k, v) in raw.items()
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
        if key[len('calendarium/'):] in ['093-3', '093-5', '093-6']:
            append[key] = entries
        else:
            sundays_and_ferias = [x for x in entries if x['qualitas'] in ['dominica', 'feria']]
            others = [x for x in entries if x not in sundays_and_ferias]
            if sundays_and_ferias:
                create[key] = sundays_and_ferias
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
    ]
    if key == 'Ant 1':
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
    elif key == 'Gloria':
        out_key = 'versiculi/gloria-patri-post-psalmum'
    elif key in versicle_keys or key in post_process_keys:
        basename = key.replace(' ', '-').lower()
        prefix = 'post-process' if key in post_process_keys else 'versiculi'
        out_key = '%s/%s' % (prefix, basename,)
    else:
        if not key in warn_keys:
            print("WARNING: Unrecognised key %s" % (key,), file=sys.stderr)
            warn_keys[key] = None
        out_key = key.lower().replace(' ', '-')
    return out_key


def make_full_path(out_key_base, out_key):
    if out_key_base is not None:
        assert out_key_base
        components = [out_key_base, out_key]
    else:
        components = [out_key]
    return '/'.join(components)



do_to_officium_psalm = {
    range(1, 151): lambda number: 'psalmi/%d' % (number,),
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


def merge_do_propers(propers, redirections, do_redirections, generic,
                     do_propers_base, do_basename, out_key_base, options):
    do_filename = os.path.join(do_propers_base, do_basename + '.txt')
    try:
        do_propers = parse(do_filename, options)
    except FileNotFoundError:
        print("Not found: %s" % (do_filename,), file=sys.stderr)
        return False
    for (do_key, value) in do_propers.items():
        if do_key == 'Rank':
            m = re.search(r'(ex|vide) (C.*)\b\s*$', do_propers[do_key][0])
            if m:
                assert out_key_base
                redirections[out_key_base] = 'commune/' + m.group(2)
        elif do_key != 'Rule':
            out_path = make_full_path(out_key_base, make_out_key(do_key,
                                                                 do_basename))
            m = re.match(r'@([^:]*)(?::([^:]*))?', value[0]) if value else None
            if m:
                redir_basename, redir_key = m.groups()
                if not redir_basename:
                    redir_basename = do_basename
                if not redir_key:
                    redir_key = do_key
                do_redirections[out_path] = (redir_basename, redir_key)
                assert 'post-process' not in out_path
            else:
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
                propers[out_path] = value
    return True


def post_process(propers, key):
    components = key.split('/')
    assert len(components) == 2

    name = components[1]
    val = propers[key]

    # XXX: Doing this unconditionally is a bit rash.
    val = [re.sub(r'^[VR]\. ', '', line) for line in val]

    if name == 'dominus':
        propers['versiculi/dominus-vobiscum'] = val[:2]
        propers['versiculi/domine-exaudi'] = val[2:4]
    elif name == 'benedicamus-domino':
        propers['versiculi/benedicamus-domino'] = val[0]
        propers['versiculi/deo-gratias'] = val[1]
    elif name == 'fidelium-animae':
        propers['versiculi/fidelium-animae'] = val[0]
        propers['versiculi/amen'] = val[1]
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
    else:
        assert False, name

    del propers[key]


def propers(calendar, options):
    propers = {}
    generic = {}
    redirections = {}
    do_redirections = {}
    do_filename_to_officium = {}

    do_propers_base = os.path.join(options.do_basedir, 'web', 'www', 'horas',
                                   'Latin')

    def merge():
        do_filename_to_officium[do_basename] = out_key_base
        return merge_do_propers(propers, redirections, do_redirections, generic,
                                do_propers_base, do_basename, out_key_base, options)

    for (entry, descs) in calendar.dictionary.items():
        if not entry.startswith('calendarium/'):
            continue
        calpoint = entry[len('calendarium/'):]
        do_calpoint = re.sub(r'Pent(\d)-', r'Pent0\1-', calpoint)
        do_basename = os.path.join(
            'Sancti' if re.match(r'\d\d-\d\d$', calpoint) else 'Tempora',
            do_calpoint,
        )
        out_key_base = 'proprium/%s' % (descs[0].get('titulus', calpoint),)
        merge()

    for common in (key[8:] for key in redirections.values()
                   if key.startswith('commune/')):
        do_basename = os.path.join('Commune', common)
        out_key_base = 'commune/%s' % (common,)
        merge()

    for basename in ["Psalmi major", "Major Special", "Prayers"]:
        do_basename = os.path.join('Psalterium', basename)
        out_key_base = None
        merge()

    for psalm_range in do_to_officium_psalm:
        for psalm in psalm_range:
            with open(os.path.join(do_propers_base, 'psalms1',
                                   'Psalm%d.txt' % (psalm,))) as f:
                raw = [line.strip() for line in f.readlines()]
            propers['psalterium/' + do_to_officium_psalm[psalm_range](psalm)] = raw

    for key in list(propers.keys()):
        if key.startswith('post-process'):
            post_process(propers, key)
        else:
            assert 'post-process' not in key

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
        if value and value[-1].startswith('$'):
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
    parser.add_argument('--rubrics', '-r', choices=['Rubrics 1960'],
                        default='Rubrics 1960')
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('datafile')
    return parser.parse_args()


def main(options):
    out = parse(options.datafile, options)

    if options.format != 'raw':
        out = calendar(out)
        from_propers = propers(bringup.make_generic('rubricarum', out), options)
        if options.format == 'propers':
            out = from_propers
        else:
            assert options.format == 'generic'
            out += from_propers

    print(yaml.dump(out, allow_unicode=True, Dumper=yaml.CDumper))


if __name__ == '__main__':
    main(parse_args())
