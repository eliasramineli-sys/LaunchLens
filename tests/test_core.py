import numpy as np
import pytest
from launchlens.data import generate_data, chronological_split, validate_features
from launchlens.config import FEATURES
from launchlens.modeling import recommend

def test_data_and_no_leakage():
    h,c=generate_data()
    assert len(h)==5000 and len(c)==60
    assert 'sucesso_12m' not in c
    assert list(validate_features(h))==FEATURES
    a,b,d=chronological_split(h)
    assert a.data_desfecho.max()<b.data_avaliacao.min()
    assert b.data_desfecho.max()<d.data_avaliacao.min()
    assert not set(a.app_id)&set(d.app_id)

def test_bad_input():
    _,c=generate_data()
    c.loc[0,'retencao_beta_d7']=2
    with pytest.raises(ValueError):validate_features(c)

def test_policy_boundaries():
    assert list(recommend(np.array([.39,.4,.6,.9]),.5))==['Adiar','Validar mais','Lancar','Lancar']
