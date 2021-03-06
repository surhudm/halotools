"""
"""
from __future__ import absolute_import, division, print_function

from astropy.tests.helper import pytest

import numpy as np
from copy import deepcopy

from ...factories import HodModelFactory, PrebuiltHodModelFactory

from ....sim_manager import FakeSim
from ....empirical_models import zheng07_model_dictionary, OccupationComponent
from ....custom_exceptions import HalotoolsError

__all__ = ('test_empty_arguments', )


def test_empty_arguments():
    with pytest.raises(HalotoolsError) as err:
        model = HodModelFactory()
    substr = "You did not pass any model features to the factory"
    assert substr in err.value.args[0]


def test_Num_ptcl_requirement():
    """ Demonstrate that passing in varying values for
    Num_ptcl_requirement results in the proper behavior.
    """
    model = PrebuiltHodModelFactory('zheng07')
    halocat = FakeSim()
    actual_mvir_min = halocat.halo_table['halo_mvir'].min()

    model.populate_mock(halocat)
    default_mvir_min = model.mock.particle_mass*model.mock.Num_ptcl_requirement
    # verify that the cut was applied
    assert np.all(model.mock.halo_table['halo_mvir'] > default_mvir_min)
    # verify that the cut was non-trivial
    assert np.any(halocat.halo_table['halo_mvir'] < default_mvir_min)

    del model.mock
    model.populate_mock(halocat, Num_ptcl_requirement=0.)
    assert model.mock.Num_ptcl_requirement == 0.
    assert np.any(model.mock.halo_table['halo_mvir'] < default_mvir_min)


def test_unavailable_haloprop():
    halocat = FakeSim()
    m = PrebuiltHodModelFactory('zheng07')
    m._haloprop_list.append("Jose Canseco")
    with pytest.raises(HalotoolsError) as err:
        m.populate_mock(halocat=halocat)
    substr = "this column is not available in the catalog you attempted to populate"
    assert substr in err.value.args[0]
    assert "``Jose Canseco``" in err.value.args[0]


def test_unavailable_upid():
    halocat = FakeSim()
    del halocat.halo_table['halo_upid']
    m = PrebuiltHodModelFactory('zheng07')

    with pytest.raises(HalotoolsError) as err:
        m.populate_mock(halocat=halocat)
    substr = "does not have the ``halo_upid`` column."
    assert substr in err.value.args[0]


def test_censat_consistency_check():
    """
    This test verifies that an informative exception will be raised if
    a satellite OccupationComponent implements the ``cenocc_model`` feature
    in a way that is inconsistent with the actual central occupation component
    used in the composite model.

    See https://github.com/astropy/halotools/issues/577 for context.
    """
    model = HodModelFactory(**zheng07_model_dictionary(modulate_with_cenocc=True))
    model._test_censat_occupation_consistency(model.model_dictionary)

    class DummySatComponent(OccupationComponent):
        def __init__(self):
            self.central_occupation_model = 43
            self.gal_type = 'satellites'

    model.model_dictionary['dummy_key'] = DummySatComponent()
    with pytest.raises(HalotoolsError) as err:
        model._test_censat_occupation_consistency(model.model_dictionary)
    substr = "has a ``central_occupation_model`` attribute with an inconsistent "
    assert substr in err.value.args[0]


def test_factory_constructor_redshift1():
    """ Verify that redundantly passing in a compatible redshift causes no problems
    """
    model_dict1 = zheng07_model_dictionary(redshift=1)
    model1 = HodModelFactory(**model_dict1)
    assert model1.redshift == 1

    model_dict2 = deepcopy(model_dict1)
    model_dict2['redshift'] = 1
    model2 = HodModelFactory(**model_dict2)
    assert model2.redshift == 1


def test_factory_constructor_redshift2():
    """ Verify that passing in an incompatible redshift raises the correct exception
    """
    model_dict1 = zheng07_model_dictionary(redshift=1)
    model1 = HodModelFactory(**model_dict1)
    assert model1.redshift == 1

    model_dict2 = deepcopy(model_dict1)
    model_dict2['redshift'] = 2
    #
    with pytest.raises(AssertionError) as err:
        model2 = HodModelFactory(**model_dict2)
    substr = "that is inconsistent with the redshift z ="
    assert substr in err.value.args[0]


def test_factory_constructor_redshift3():
    """ Verify correct redshift behavior when using the baseline_model_instance argument
    """
    model_dict1 = zheng07_model_dictionary(redshift=1)
    model1 = HodModelFactory(**model_dict1)

    model2 = HodModelFactory(baseline_model_instance=model1,
            redshift=model1.redshift)

    assert model2.redshift == model1.redshift

    with pytest.raises(AssertionError) as err:
        model3 = HodModelFactory(baseline_model_instance=model1,
                redshift=model1.redshift+1)
    substr = "that is inconsistent with the redshift z ="
    assert substr in err.value.args[0]


def test_factory_constructor_redshift4():
    """ Verify correct redshift behavior when the model dictionary
    has no components with redshifts defined
    """
    model_dict_no_redshift = zheng07_model_dictionary(redshift=1)
    for component_model in model_dict_no_redshift.values():
        del component_model.redshift

    model_dict_no_redshift['redshift'] = 1.5
    model2 = HodModelFactory(**model_dict_no_redshift)
    assert model2.redshift == 1.5
