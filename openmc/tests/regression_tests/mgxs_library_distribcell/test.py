import hashlib
import sys

import openmc
import openmc.mgxs
from openmc.examples import pwr_assembly
import pytest

from tests.testing_harness import PyAPITestHarness


class MGXSTestHarness(PyAPITestHarness):
    def __init__(self, *args, **kwargs):
        # Generate inputs using parent class routine
        super().__init__(*args, **kwargs)

        # Initialize a one-group structure
        energy_groups = openmc.mgxs.EnergyGroups(group_edges=[0, 20.e6])

        # Initialize MGXS Library for a few cross section types
        # for one material-filled cell in the geometry
        self.mgxs_lib = openmc.mgxs.Library(self._model.geometry)
        self.mgxs_lib.by_nuclide = False

        # Test all relevant MGXS types
        relevant_MGXS_TYPES = [item for item in openmc.mgxs.MGXS_TYPES
                               if item != 'current']
        self.mgxs_lib.mgxs_types = tuple(relevant_MGXS_TYPES) + \
                                   openmc.mgxs.MDGXS_TYPES
        self.mgxs_lib.energy_groups = energy_groups
        self.mgxs_lib.num_delayed_groups = 6
        self.mgxs_lib.legendre_order = 3
        self.mgxs_lib.domain_type = 'distribcell'
        cells = self.mgxs_lib.geometry.get_all_material_cells().values()
        self.mgxs_lib.domains = [c for c in cells if c.name == 'fuel']
        self.mgxs_lib.build_library()

        # Add tallies
        self.mgxs_lib.add_to_tallies_file(self._model.tallies, merge=False)
        self._model.tallies.export_to_xml()

    def _get_results(self, hash_output=False):
        """Digest info in the statepoint and return as a string."""

        # Read the statepoint file.
        sp = openmc.StatePoint(self._sp_name)

        # Load the MGXS library from the statepoint
        self.mgxs_lib.load_from_statepoint(sp)

        # Average the MGXS across distribcell subdomains
        avg_lib = self.mgxs_lib.get_subdomain_avg_library()

        # Build a string from Pandas Dataframe for each 1-group MGXS
        outstr = ''
        for domain in avg_lib.domains:
            for mgxs_type in avg_lib.mgxs_types:
                mgxs = avg_lib.get_mgxs(domain, mgxs_type)
                df = mgxs.get_pandas_dataframe()
                outstr += df.to_string() + '\n'

        # Hash the results if necessary
        if hash_output:
            sha512 = hashlib.sha512()
            sha512.update(outstr.encode('utf-8'))
            outstr = sha512.hexdigest()

        return outstr


def test_mgxs_library_distribcell():
    model = pwr_assembly()
    harness = MGXSTestHarness('statepoint.10.h5', model)
    harness.main()
