import re
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
            self.add_virtual_dataset("params", params)
        except Exception as e:
            print(e)
            print("Couldn't find expid")

        try:
            THRESHOLD = 1
            Y_MAX = 1

            raw_counts = h5utils.get_dataset(self, "raw")
            num_points = len(raw_counts)
            num_shots  = len(raw_counts["0"])
            num_pmt    = len(raw_counts["0"][0])

            pmt_data = np.zeros((num_pmt, num_points))
            pmt_err  = np.zeros((num_pmt, num_points))

            for i in range(num_points):
                point_data = np.array(raw_counts[str(i)]).transpose()  # (num_pmt, num_shots)
                for pmt in range(num_pmt):
                    pmt_data[pmt][i] = np.mean(point_data[pmt] > THRESHOLD)

            for pmt in range(num_pmt):
                for i in range(num_points):
                    perr = np.sqrt(pmt_data[pmt][i] * (Y_MAX - pmt_data[pmt][i]) / num_shots)
                    pmt_err[pmt][i] = 0.0 if perr == 0 else perr

            for pmt in range(num_pmt):
                vidx = pmt - (num_pmt // 2)
                self.add_virtual_dataset(f"pops_{vidx}", pmt_data[pmt])
                self.add_virtual_dataset(f"errs_{vidx}", pmt_err[pmt])

            self.add_virtual_dataset("num_points", num_points)
            self.add_virtual_dataset("num_shots",  num_shots)

        except Exception as e:
            print(e)
            print("Error finding/processing PMT data")

        # -- scan axis + active PMTs -----------------------------------------------
        self._scan_x    = None
        self._scan_name = None
        self.active_pmts = []
        try:
            sg = self['datasets/scan']
            for k in sg.keys():
                if k == 'product':
                    continue
                try:
                    arr = np.asarray(sg[k][()])
                    if arr.ndim == 1 and len(arr) > 1 and np.issubdtype(arr.dtype, np.number):
                        self._scan_x    = arr
                        self._scan_name = k
                        break
                except Exception:
                    pass
        except Exception:
            pass
        # public alias so users can write f.x instead of f._scan_x
        object.__setattr__(self, 'x', self._scan_x)

        try:
            active = []
            for k in self.keys():
                if not k.startswith('pops_'):
                    continue
                try:
                    if np.mean(self[k][()]) > 0.05:
                        active.append(int(k[5:]))
                except Exception:
                    pass
            self.active_pmts = sorted(active, key=abs)
            if self.active_pmts:
                print(f"Active PMTs: {self.active_pmts}")
        except Exception:
            pass

    # -- virtual dataset registry ------------------------------------------

    def add_virtual_dataset(self, name: str, value):
        """Register a virtual dataset (or dict -> VirtualGroup) under name."""
        self._virtual_datasets[name] = _wrap(value, name=f"/{name}")

    # -- transparent proxy to real + virtual ------------------------------

    def __getitem__(self, key: str):
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
        super().visititems(func)
        for vname, vobj in self._virtual_datasets.items():
            if isinstance(vobj, _VirtualGroup):
                vobj.visititems(lambda name, obj: func(f"{vname}/{name}", obj))
            else:
                func(vname, vobj)

    def items(self):
        real    = list(super().items())
        virtual = list(self._virtual_datasets.items())
        return real + virtual

    def keys(self):
        from itertools import chain
        return list(chain(super().keys(), self._virtual_datasets.keys()))

    # -- dot-access for populations ----------------------------------------

    def __getattr__(self, name):
        # guard: private attrs and real h5py attrs come first via normal lookup
        if name.startswith('_'):
            raise AttributeError(name)

        from .series import Series
        from .h5utils import joint_pop as _jp

        x = object.__getattribute__(self, '_scan_x')
        n_pts = len(x) if x is not None else None

        def _x_for(y):
            return x if x is not None else np.arange(len(y))

        # p{bits}_err  →  joint population error array
        m = re.fullmatch(r'p([01]+)_err', name)
        if m:
            _, err = _jp(self, m.group(1))
            return err

        # p{bits}  →  unmanaged Series (y = joint pop, yerr = joint err)
        m = re.fullmatch(r'p([01]+)', name)
        if m:
            state = m.group(1)
            y, yerr = _jp(self, state)
            return Series(_x_for(y), y, yerr=yerr, label=state)

        # pmt{n}_err  →  individual PMT error array  (n = non-negative integer)
        m = re.fullmatch(r'pmt(\d+)_err', name)
        if m:
            idx  = int(m.group(1))
            return np.asarray(self[f'errs_{idx}'][()])

        # pmt{n}  →  unmanaged Series for individual PMT
        m = re.fullmatch(r'pmt(\d+)', name)
        if m:
            idx  = int(m.group(1))
            y    = np.asarray(self[f'pops_{idx}'][()])
            yerr = np.asarray(self[f'errs_{idx}'][()])
            return Series(_x_for(y), y, yerr=yerr, label=f'pmt{idx}')

        raise AttributeError(f"GoldH5File has no attribute '{name}'")

    def __repr__(self):
        try:
            fname = self.filename
        except Exception:
            fname = '?'
        return f"<GoldH5File '{fname}' | active_pmts={self.active_pmts}>"
