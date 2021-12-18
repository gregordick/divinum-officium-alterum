from abc import ABC, abstractmethod

from officium import data


class Psalmish(ABC):
    def __init__(self, key):
        self.key = 'psalterium/' + key

    @property
    @abstractmethod
    def conclusion(self):
        raise NotImplementedError("This method should be overridden.")


class PsalmishWithGloria(Psalmish):
    conclusion = 'versiculi/gloria-patri-post-psalmum'

class PsalmishWithoutGloria(Psalmish):
    conclusion = None

class PsalmishWithRequiem(Psalmish):
    conclusion = 'versiculi/requiem-aeternam-post-psalmum'


labels = {
    'sine-gloria': PsalmishWithoutGloria
}
def descriptor_to_psalmish(descriptor, default_class=PsalmishWithGloria):
    cls, arg, meta = data.maybe_labelled(descriptor, labels, default_class)
    return cls(arg, **meta)
