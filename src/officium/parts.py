class Group:
    def __init__(self, contents):
        self.contents = contents

    def resolve(self):
        for content in self.contents:
            yield content


class Text:
    def __init__(self, text):
        self.text = text

    def render(self):
        return self.text


class Chapter(Group): pass
class Hymn(Group): pass
class Versicle(Group): pass
class VersicleResponse(Group): pass
class Oration(Group): pass


class PsalmishWithAntiphon:
    def __init__(self, antiphon, psalmishes):
        self.antiphon = antiphon
        self.psalmishes = psalmishes

    def resolve(self):
        # XXX: Proper classes, Gloria.
        yield Text(self.antiphon)
        for psalmish in self.psalmishes:
            yield Text(psalmish)
        yield Text(self.antiphon)


def deus_in_adjutorium():
    def generator():
        yield Versicle([Text('versiculi/deus-in-adjutorium')])
        yield VersicleResponse([Text('versiculi/domine-ad-adjuvandum')])
        yield Text('versiculi/gloria-patri')
        yield Text('versiculi/sicut-erat')
        yield Text('versiculi/alleluja')
    return Group(generator())


def dominus_vobiscum():
    def generator():
        yield Versicle([Text('versiculi/dominus-vobiscum')])
        yield VersicleResponse([Text('versiculi/et-cum-spiritu-tuo')])
    return Group(generator())
