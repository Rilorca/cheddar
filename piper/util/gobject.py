from typing import Callable, Union

from gi.repository import GObject


def connect_signal_with_weak_ref(
    ref_obj: Union[GObject.Object, GObject.GObject],
    obj: Union[GObject.Object, GObject.GObject],
    signal: str,
    func: Callable,
    *args,
) -> int:
    """
    Connect handler to an object `obj` tied to the life time of `ref_obj`.

    Use this to work around https://gitlab.gnome.org/GNOME/pygobject/-/issues/557.
    """

    handler = obj.connect(signal, func, *args)
    ref_obj.weak_ref(lambda: obj.disconnect(handler))
    return handler
