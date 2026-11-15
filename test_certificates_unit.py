import pytest
from fastapi import HTTPException

from app.application.use_cases.certificates import (
    _mask,
    _validate_request,
    provider_catalog,
    validate_cnpj,
    validate_cpf,
)


@pytest.mark.parametrize("value", ["529.982.247-25", "11144477735"])
def test_validate_cpf_accepts_valid_values(value):
    assert validate_cpf(value)


@pytest.mark.parametrize("value", ["111.111.111-11", "529.982.247-24", "123"])
def test_validate_cpf_rejects_invalid_values(value):
    assert not validate_cpf(value)


def test_validate_cnpj_accepts_valid_value():
    assert validate_cnpj("11.222.333/0001-81")


def test_validate_cnpj_rejects_repeated_digits():
    assert not validate_cnpj("11.111.111/1111-11")


def test_provider_requirements_are_validated_before_creating_request():
    with pytest.raises(HTTPException) as error:
        _validate_request("policia-federal", {"document": "52998224725"})
    assert error.value.status_code == 422


def test_sefaz_only_accepts_prepared_minas_gerais_connector():
    with pytest.raises(HTTPException) as error:
        _validate_request("sefaz", {"document": "11222333000181", "uf": "SP"})
    assert error.value.status_code == 422


def test_unexpected_form_fields_are_rejected():
    with pytest.raises(HTTPException) as error:
        _validate_request("receita-federal", {"document": "52998224725", "nome": "Pessoa"})
    assert error.value.status_code == 422


def test_catalog_never_claims_automated_api_or_real_issuance():
    catalog = provider_catalog()
    assert len(catalog) == 6
    assert all(item["apiAvailable"] is False for item in catalog)
    assert all(item["integrationMode"] == "OFFICIAL_PORTAL" for item in catalog)


def test_identifier_mask_does_not_expose_full_document():
    assert _mask("52998224725") == "***.***.247-**"
