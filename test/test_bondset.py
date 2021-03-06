import unittest

import logging

from pycgtool.bondset import BondSet
from pycgtool.frame import Frame
from pycgtool.mapping import Mapping
from pycgtool.util import cmp_whitespace_float

try:
    import mdtraj
    mdtraj_present = True
except ImportError:
    mdtraj_present = False


class DummyOptions:
    constr_threshold = 100000
    map_center = "geom"
    angle_default_fc = False
    generate_angles = True
    generate_dihedrals = False


class BondSetTest(unittest.TestCase):
    # Columns are: eqm value, standard fc, defaults fc, mixed fc
    invert_test_ref_data = [
        (  0.220474419132,  72658.18163, 1250, 1520530.416),
        (  0.221844516963,  64300.01188, 1250, 1328761.015),
        (  0.216313356504,  67934.93368, 1250, 1474281.672),
        (  0.253166204438,  19545.27388, 1250,  311446.690),
        (  0.205958461836,  55359.06367, 1250, 1322605.992),
        (  0.180550961226, 139643.66601, 1250, 4334538.941),
        ( 77.882969526805,    503.24211,   25,     481.527),
        (116.081406627900,    837.76904,   25,     676.511),
        (111.030514958715,    732.87969,   25,     639.007),
        ( 83.284691301386,    945.32633,   25,     933.199),
        (143.479514279933,    771.63691,   25,     273.207),
        ( 99.293754667718,    799.82825,   25,     779.747),
        (-82.852665692244,    253.75691,   50,    1250),
        ( 61.159604648237,    125.04591,   50,    1250),
        (-21.401629717440,    135.50927,   50,    1250),
        ( 53.161150086611,     51.13975,   50,    1250),
        (-96.548945531698,     59.38162,   50,    1250),
        ( 75.370211843364,    279.80889,   50,    1250)
    ]

    def test_bondset_create(self):
        measure = BondSet("test/data/sugar.bnd", DummyOptions)
        self.assertEqual(1, len(measure))
        self.assertTrue("ALLA" in measure)
        self.assertEqual(18, len(measure["ALLA"]))

    def test_bondset_apply(self):
        measure = BondSet("test/data/sugar.bnd", DummyOptions)
        frame = Frame("test/data/sugar-cg.gro")
        measure.apply(frame)
        # First six are bond lengths
        self.assertEqual(1, len(measure["ALLA"][0].values))
        self.assertAlmostEqual(0.2225376, measure["ALLA"][0].values[0],
                               delta=0.2225376 / 500)
        # Second six are angles
        self.assertEqual(1, len(measure["ALLA"][6].values))
        self.assertAlmostEqual(77.22779289, measure["ALLA"][6].values[0],
                               delta=77.22779289 / 500)
        # Final six are dihedrals
        self.assertEqual(1, len(measure["ALLA"][12].values))
        self.assertAlmostEqual(-89.5552903, measure["ALLA"][12].values[0],
                               delta=89.552903 / 500)

    def test_bondset_remove_triangles(self):
        bondset = BondSet("test/data/triangle.bnd", DummyOptions)
        angles = bondset.get_bond_angles("TRI", exclude_triangle=False)
        self.assertEqual(3, len(angles))
        angles = bondset.get_bond_angles("TRI", exclude_triangle=True)
        self.assertEqual(0, len(angles))

    def support_check_mean_fc(self, mol_bonds, fc_column_number):
        # Require accuracy to 0.5%
        # Allows for slight modifications to code
        accuracy = 0.005

        for i, bond in enumerate(mol_bonds):
            ref = self.invert_test_ref_data
            self.assertAlmostEqual(ref[i][0], bond.eqm,
                                   delta=abs(ref[i][0] * accuracy))
            self.assertAlmostEqual(ref[i][fc_column_number], bond.fconst,
                                   delta=abs(ref[i][fc_column_number] * accuracy))

    def test_bondset_boltzmann_invert(self):
        measure = BondSet("test/data/sugar.bnd", DummyOptions)
        frame = Frame("test/data/sugar.gro", xtc="test/data/sugar.xtc")
        mapping = Mapping("test/data/sugar.map", DummyOptions)

        cgframe = mapping.apply(frame)
        while frame.next_frame():
            cgframe = mapping.apply(frame, cgframe=cgframe)
            measure.apply(cgframe)

        measure.boltzmann_invert()
        self.support_check_mean_fc(measure["ALLA"], 1)

    def test_bondset_boltzmann_invert_default_fc(self):
        class DefaultOptions(DummyOptions):
            default_fc = True

        measure = BondSet("test/data/sugar.bnd", DefaultOptions)
        frame = Frame("test/data/sugar.gro", xtc="test/data/sugar.xtc")
        mapping = Mapping("test/data/sugar.map", DefaultOptions)

        cgframe = mapping.apply(frame)
        while frame.next_frame():
            cgframe = mapping.apply(frame, cgframe=cgframe)
            measure.apply(cgframe)

        measure.boltzmann_invert()
        self.support_check_mean_fc(measure["ALLA"], 2)

    def test_bondset_boltzmann_invert_func_forms(self):
        class FuncFormOptions(DummyOptions):
            length_form = "CosHarmonic"
            angle_form = "Harmonic"
            dihedral_form = "MartiniDefaultLength"

        measure = BondSet("test/data/sugar.bnd", FuncFormOptions)
        frame = Frame("test/data/sugar.gro", xtc="test/data/sugar.xtc")
        mapping = Mapping("test/data/sugar.map", DummyOptions)

        cgframe = mapping.apply(frame)
        while frame.next_frame():
            cgframe = mapping.apply(frame, cgframe=cgframe)
            measure.apply(cgframe)

        measure.boltzmann_invert()
        self.support_check_mean_fc(measure["ALLA"], 3)

    @unittest.skipIf(not mdtraj_present, "MDTRAJ or Scipy not present")
    def test_bondset_boltzmann_invert_mdtraj(self):
        logging.disable(logging.WARNING)
        frame = Frame("test/data/sugar.gro", xtc="test/data/sugar.xtc",
                      xtc_reader="mdtraj")
        logging.disable(logging.NOTSET)

        measure = BondSet("test/data/sugar.bnd", DummyOptions)
        mapping = Mapping("test/data/sugar.map", DummyOptions)

        cgframe = mapping.apply(frame)
        while frame.next_frame():
            cgframe = mapping.apply(frame, cgframe=cgframe)
            measure.apply(cgframe)

        measure.boltzmann_invert()
        self.support_check_mean_fc(measure["ALLA"], 1)

    def test_bondset_polymer(self):
        bondset = BondSet("test/data/polyethene.bnd", DummyOptions)
        frame = Frame("test/data/polyethene.gro")
        bondset.apply(frame)
        self.assertEqual(5, len(bondset["ETH"][0].values))
        self.assertEqual(4, len(bondset["ETH"][1].values))
        self.assertEqual(4, len(bondset["ETH"][2].values))
        self.assertEqual(4, len(bondset["ETH"][3].values))
        bondset.boltzmann_invert()
        self.assertAlmostEqual(0.107, bondset["ETH"][0].eqm,
                               delta=0.107 / 500)
        self.assertAlmostEqual(0.107, bondset["ETH"][1].eqm,
                               delta=0.107 / 500)

    def test_bondset_pbc(self):
        bondset = BondSet("test/data/polyethene.bnd", DummyOptions)
        frame = Frame("test/data/pbcpolyethene.gro")
        bondset.apply(frame)
        bondset.boltzmann_invert()
        for bond in bondset.get_bond_lengths("ETH", True):
            self.assertAlmostEqual(1., bond.eqm)
            self.assertEqual(float("inf"), bond.fconst)

    def test_full_itp_sugar(self):
        measure = BondSet("test/data/sugar.bnd", DummyOptions)
        frame = Frame("test/data/sugar.gro", xtc="test/data/sugar.xtc")
        mapping = Mapping("test/data/sugar.map", DummyOptions)
        cgframe = mapping.apply(frame)

        while frame.next_frame():
            cgframe = mapping.apply(frame, cgframe=cgframe)
            measure.apply(cgframe)

        measure.boltzmann_invert()

        logging.disable(logging.WARNING)
        measure.write_itp("sugar_out.itp", mapping)
        logging.disable(logging.NOTSET)

        self.assertTrue(cmp_whitespace_float("sugar_out.itp", "test/data/sugar_out.itp", float_rel_error=0.001))
