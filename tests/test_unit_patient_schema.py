import pytest
from pydantic import ValidationError

from app.schemas.patient import PatientCreate


def test_patient_create_age_validation():
    with pytest.raises(ValidationError):
        PatientCreate(full_name="Kid", age=0)


def test_patient_create_defaults():
    payload = PatientCreate(full_name="Kid", age=9)
    assert payload.notes == ""
    assert payload.sensory_profile == {}
