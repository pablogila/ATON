"""
# Description

The `System` object contains all the information needed for a single QRotor calculation.
This class can be loaded directly as `aton.qrotor.System()`.

---
"""


import numpy as np
from .constants import *
from aton.st import alias
from aton._version import __version__


class System:
    """Quantum system.

    Contains all the data for a single QRotor calculation, with both inputs and outputs.
    """
    def __init__(
            self,
            comment: str = None,
            group: str = 'CH3',
            E_levels: int = 15,
            correct_potential_offset: bool = True,
            save_eigenvectors: bool = True,
            gridsize: int = 200000,
            grid = [],
            B: float = None,
            potential_name: str = '',
            potential_constants: list = None,
            potential_values = [],
            ):
        ## Technical
        self.version = __version__
        """Version of the package used to generate the data."""
        self.comment: str = comment
        """Custom comment for the dataset."""
        self.group: str = group
        """Chemical group, methyl or amine: `'CH3'`, `'CD3'`, `'NH3'`, `'ND3'`."""
        self.set_group(group)  # Normalise the group name, and set the value of B
        self.E_levels: int = E_levels
        """Number of energy levels to be studied."""
        self.correct_potential_offset: bool = correct_potential_offset
        """Correct the potential offset as `V - min(V)` or not."""
        self.save_eigenvectors: bool = save_eigenvectors
        """Save or not the eigenvectors. Final file size will be bigger."""
        ## Potential
        self.gridsize: int = gridsize
        """Number of points in the grid."""
        self.grid = grid
        """The grid with the points to be used in the calculation.

        Can be set automatically over $2 \\pi$ with `System.set_grid()`.
        Units must be in radians.
        """
        if not B:
            B = self.B
        self.B: float = B
        """Rotational inertia, as in $B=\\frac{\\hbar^2}{2I}$."""
        self.potential_name: str = potential_name
        """Name of the desired potential: `'zero'`, `'titov2023'`, `'test'`...
        If empty or unrecognised, the custom potential values inside `System.potential_values` will be used. 
        """
        self.potential_constants: list = potential_constants
        """List of constants to be used in the calculation of the potential energy, in the `aton.qrotor.potential` module."""
        self.potential_values = potential_values
        """Numpy ndarray with the potential values for each point in the grid.

        Can be calculated with a function available in the `qrotor.potential` module,
        or loaded externally with the `qrotor.potential.load()` function.
        Potential energy units must be in meV.
        """
        self.potential_offset: float = None
        """`min(V)` before offset correction when `correct_potential_offset = True`"""
        self.potential_min: float = None
        """`min(V)`"""
        self.potential_max: float = None
        """`max(V)`"""
        # Energies
        self.eigenvalues = []
        """Calculated eigenvalues of the system. Should be in meV."""
        self.eigenvectors = []
        """Eigenvectors, if `save_eigenvectors` is True. Beware of the file size."""
        self.energy_barrier: float = None
        """`max(V) - min(eigenvalues)`"""
        self.transitions: list = None
        """eigenvalues[i+1] - eigenvalues[0]"""
        self.runtime: float = None
        """Time taken to solve the eigenvalues."""

    def summary(self):
        return {
            'version': self.version,
            'comment': self.comment,
            'group': self.group,
            'gridsize': self.gridsize,
            'B': self.B,
            'potential_name': self.potential_name,
            'potential_constants': self.potential_constants.tolist() if isinstance(self.potential_constants, np.ndarray) else self.potential_constants,
            'potential_offset': self.corrected_potential_offset,
            'potential_min': self.potential_min,
            'potential_max': self.potential_max,
            'eigenvalues': self.eigenvalues.tolist() if isinstance(self.eigenvalues, np.ndarray) else self.eigenvalues,
            'energy_barrier': self.energy_barrier,
            'transitions': self.transitions,
            'runtime': self.runtime,
        }

    def set_grid(self, gridsize:int=None):
        """Sets the `System.grid` to the specified `gridsize` from 0 to $2\\pi$.

        If the system had a previous grid and potential values,
        it will interpolate those values to the new gridsize,
        using `aton.qrotor.potential.interpolate()`.
        """
        if gridsize == self.gridsize:
            return self  # Nothing to do here
        if gridsize:
            self.gridsize = gridsize
        # Should we interpolate?
        if any(self.potential_values) and any(self.grid) and self.gridsize:
            from .potential import interpolate
            self = interpolate(self)
        # Should we create the values from zero?
        elif self.gridsize:
                self.grid = np.linspace(0, 2*np.pi, self.gridsize)
        else:
            raise ValueError('gridsize must be provided if there is no System.gridsize')
        return self
    
    def set_group(self, group:str=None, B:float=None):
        """Normalise `System.group` name, and set `System.B` based on it."""
        for name in alias.chemical['CH3']:
            if group.lower() == name:
                self.group = 'CH3'
                if not B:
                    B = B_CH3
                self.B = B
                return self
        for name in alias.chemical['CD3']:
            if group.lower() == name:
                self.group = 'CD3'
                if not B:
                    B = B_CD3
                self.B = B
                return self
        for name in alias.chemical['NH3']:
            if group.lower() == name:
                self.group = 'NH3'
                if not B:
                    B = B_NH3
                self.B = B
                return self
        for name in alias.chemical['ND3']:
            if group.lower() == name:
                self.group = 'ND3'
                if not B:
                    B = B_ND3
                self.B = B
                return self
        self.group = group  # No match was found
        return self
    
    def solve(self, new_gridsize:int=None):
        """Solves the quantum system.

        The potential can be interpolated to a `new_gridsize`.
    
        Same as running `aton.qrotor.solve.energies(System)`.
        """
        from .solve import energies
        if new_gridsize:
            self.gridsize = new_gridsize
        return energies(self)

    def reduce_size(self):
        """Discard data that takes too much space,
        like eigenvectors, potential values and grids."""
        self.eigenvectors = []
        self.potential_values = []
        self.grid = []
        return self

