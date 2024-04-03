import sys
import logging
from importlib.abc import MetaPathFinder, Loader


logger = logging.getLogger("importhook")

_hooks = {}  # name -> [list of funcs]


def on_import(fullname, func=None):
    """Register a function to be called when fullname is imported. Can be used as a decorator."""

    def on_import_wrapper(func):
        _hooks.setdefault(fullname, []).append(func)
        return func

    if func is not None:
        return on_import_wrapper(func)
    else:
        return on_import_wrapper


class ImporthookLoader(Loader):
    def __init__(self, loader, fullname, hook_funcs):
        self.__loader = loader
        self.__fullname = fullname
        self.__hook_funcs = hook_funcs
        cls = self.__class__
        for name in dir(loader):
            if not name.startswith("_") and not hasattr(cls, name):
                ob = getattr(loader, name)
                if callable(ob):
                    setattr(self, name, ob)

    def __repr__(self):
        f"<ImporthookLoader for {self.__fullname}: {self.__loader}>"

    def exec_module(self, m, *args, **kwargs):
        result = self.__loader.exec_module(m, *args, **kwargs)
        for hook_func in self.__hook_funcs:
            try:
                hook_func(m)
            except Exception as err:
                logger.error(
                    f"Error in import hook for {self.__fullname}, func {hook_func}: {err}"
                )
        return result


class ImporthookMetaPathFinder(MetaPathFinder):
    def find_spec(self, fullname, *args, **kwargs):

        # Do we have a hook for this import?
        hook_funcs = _hooks.get(fullname, [])

        # If so, try all finders (except this one)
        spec = None
        if hook_funcs:
            for finder in sys.meta_path:
                if finder is not self:
                    spec = finder.find_spec(fullname, *args, **kwargs)
                    if spec is not None:
                        break

        # If we found a spec, return our wrapping loader
        if spec is not None:
            spec.loader = ImporthookLoader(spec.loader, fullname, hook_funcs)
            return spec
        else:
            return None


# Register the custom finder.
sys.meta_path.insert(0, ImporthookMetaPathFinder())
