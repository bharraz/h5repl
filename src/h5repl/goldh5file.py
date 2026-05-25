import h5py
import json
import numpy as np
from . import h5utils

def _wrap(value, name=None):
    """Recursively wrap a value as VirtualGroup or VirtualDataset."""
    if isinstance(value, dict):
        return _VirtualGroup(value, name=name)
    return _VirtualDataset(value, name=name)


class _VirtualDataset:
    def __init__(self, value, name=None):
        self.value = value
        self.name = name
        arr = np.asarray(value)
        self.shape = arr.shape
        self.dtype = arr.dtype

    def __getitem__(self, item):
        if item == () or item == slice(None):
            return self.value
        return self.value[item]

    def __repr__(self):
        name_str = self.name or "<anonymous>"
        return f'<VirtualDataset "{name_str}": shape={self.shape}, dtype={self.dtype}>'


class _VirtualGroup:
    def __init__(self, data: dict, name=None):
        self._data = data
        self.name = name

    def __getitem__(self, key: str):
        parts = key.split("/", 1)
        raw = self._data[parts[0]]
        child_name = f"{self.name}/{parts[0]}" if self.name else parts[0]
        wrapped = _wrap(raw, name=child_name)
        if len(parts) == 1:
            return wrapped
        return wrapped[parts[1]]

    def __contains__(self, key: str):
        parts = key.split("/", 1)
        if parts[0] not in self._data:
            return False
        if len(parts) == 1:
            return True
        return parts[1] in _wrap(self._data[parts[0]])

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        name_str = self.name or "<anonymous>"
        return f'<VirtualGroup "{name_str}" ({len(self._data)} members)>'

    def keys(self):   return self._data.keys()
    def values(self): return (_wrap(v) for v in self._data.values())
    def items(self):
        prefix = self.name or ""
        return ((k, _wrap(v, name=f"{prefix}/{k}" if prefix else k)) for k, v in self._data.items())

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def visititems(self, func):
        def _walk(node, prefix=""):
            for k, v in node._data.items():
                path = f"{prefix}/{k}" if prefix else k
                wrapped = _wrap(v, name=f"{self.name}/{path}" if self.name else path)
                func(path, wrapped)
                if isinstance(wrapped, _VirtualGroup):
                    _walk(wrapped, path)
        _walk(self)

    def visit(self, func):
        self.visititems(lambda path, _: func(path))


class GoldH5File(h5py.File):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._virtual_datasets = {}

        try:
            eid = h5utils.get_dataset(self, "expid")
            params = json.loads(eid)["arguments"]
            # Expose the whole arguments dict as a virtual group at "params"
            self.add_virtual_dataset("params", params)
        except Exception:
            pass  # file has no expid, or wrong shape — silently skip

    # ── virtual dataset registry ──────────────────────────────────────────

    def add_virtual_dataset(self, name: str, value):
        """
        Register a virtual dataset (or dict → VirtualGroup) under `name`.
        Can be called after __init__ to attach more virtual datasets.
        """
        self._virtual_datasets[name] = _wrap(value, name=f"/{name}")

    # ── transparent proxy to real + virtual ──────────────────────────────

    def __getitem__(self, key: str):
        # Virtual datasets shadow real ones (file is read-only anyway)
        top = key.split("/", 1)[0]
        if top in self._virtual_datasets:
            node = self._virtual_datasets[top]
            rest = key[len(top):]
            if rest.startswith("/"):
                return node[rest[1:]]
            return node
        return super().__getitem__(key)

    def __contains__(self, key: str):
        top = key.split("/", 1)[0]
        if top in self._virtual_datasets:
            return True
        return super().__contains__(key)

    def visititems(self, func):
        # Walk real HDF5 datasets
        super().visititems(func)
        # Walk virtual datasets
        for vname, vobj in self._virtual_datasets.items():
            if isinstance(vobj, _VirtualGroup):
                vobj.visititems(lambda name, obj: func(f"{vname}/{name}", obj))
            else:
                func(vname, vobj)
    def items(self):
        real = list(super().items())
        virtual = list(self._virtual_datasets.items())
        return real + virtual

    def keys(self):
        # Merge real keys + virtual keys
        from itertools import chain
        return list(chain(super().keys(), self._virtual_datasets.keys()))