generic = {
    'psalterium/ad-vesperas/dominica/psalmi': [
        ['psalmi/109'],
        ['psalmi/110'],
        ['psalmi/111'],
        ['psalmi/112'],
        ['psalmi/113'],
    ],

    'psalterium/ad-vesperas/feria-ii/psalmi': [['TODO']],
    'psalterium/ad-vesperas/feria-iii/psalmi': [['TODO']],
    'psalterium/ad-vesperas/feria-iv/psalmi': [['TODO']],
    'psalterium/ad-vesperas/feria-v/psalmi': [['TODO']],
    'psalterium/ad-vesperas/feria-vi/psalmi': [['TODO']],
    'psalterium/ad-vesperas/sabbato/psalmi': [['TODO']],

    'proprium/08-15/in-assumptione-beatae-mariae-virginis/ad-vesperas/psalmi': [
        ['psalmi/109'],
        ['psalmi/112'],
        ['psalmi/121'],
        ['psalmi/126'],
        ['psalmi/147'],
    ],
}

latin = {
    'versiculi/deus-in-adjutorium': 'Deus, in adjutórium meum inténde.',
    'versiculi/domine-ad-adjuvandum': 'Dómine, ad adjuvándum me festína.',
    'versiculi/gloria-patri': 'Glória Patri, et Fílio, et Spirítui Sancto.',
    'versiculi/sicut-erat': 'Sicut erat in princípio, et nunc, et semper, et in sǽcula sæculórum.  Amen.',
    'versiculi/alleluja': 'Allelúja.',

    'psalterium/ad-vesperas/dominica/antiphonae': [
        'Dixit Dóminus * Dómino meo: Sede a dextris meis.',
        'Magna ópera Dómini: * exquisíta in omnes voluntátes ejus.',
        'Qui timet Dóminum, * in mandátis eíus cupit nimis.',
        'Sit nomen Dómini * benedíctum in sǽcula.',
        'Deus autem noster * in cælo: ómnia quæcúmque vóluit, fecit.',
    ],

    'proprium/pent-12/ad-magnificat': 'Homo quidam * descendébat ab Jerúsalem in Jéricho et íncidit in latrónes, qui étiam despoliavérunt eum et, plagis impósitis, abiérunt semivívo relícto.',
}

# OK.  So how do we do, e.g., Tridentine?  I think we _really_ want an explicit layer of indirection that we can switch out.  Probably it should default to the identity mapping.  Solution: Fit it in front of the data store object that's passed around everywhere (i.e. use a wrapper object).  Maybe we should extend this to multiple compositions, so that we can also express internal cross-references (e.g. where the Lauds antiphons happen to equal the Vespers antiphons).

# How do we handle the conclusions of prayers?
