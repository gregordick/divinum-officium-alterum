from abc import ABC, abstractmethod

from officium import data


class Psalmish(ABC):
    def __init__(self, key):
        self.key = 'psalterium/' + key

    @property
    @abstractmethod
    def gloria(self):
        raise NotImplementedError("This method should be overridden.")


class PsalmishWithGloria(Psalmish):
    gloria = True


class PsalmishWithoutGloria(Psalmish):
    gloria = False


labels = {
    'sine gloria': PsalmishWithoutGloria
}
def descriptor_to_psalmish(descriptor, default_class=PsalmishWithGloria):
    cls, arg = data.maybe_labelled(descriptor, labels, default_class)
    return cls(arg)
