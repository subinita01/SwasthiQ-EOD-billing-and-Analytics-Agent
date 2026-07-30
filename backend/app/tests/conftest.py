from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.analytics import build_analytics_report
from app.services.reconciliation import build_reconciliation_report
from app.services.validation import parse_billing_log

SAMPLE_DATA_DIR = Path(__file__).resolve().parents[2] / "sample_data"


def load_sample_raw(filename: str):
    return json.loads((SAMPLE_DATA_DIR / filename).read_text())


def load_sample_entries(filename: str):
    return parse_billing_log(load_sample_raw(filename))


@pytest.fixture
def clinic_day_1_raw():
    return load_sample_raw("clinic_day_1.json")


@pytest.fixture
def clinic_day_1():
    return load_sample_entries("clinic_day_1.json")


@pytest.fixture
def clinic_day_2():
    return load_sample_entries("clinic_day_2.json")


@pytest.fixture
def clinic_day_3():
    return load_sample_entries("clinic_day_3.json")


@pytest.fixture
def clinic_day_1_reports(clinic_day_1):
    return build_reconciliation_report(clinic_day_1), build_analytics_report(clinic_day_1)


@pytest.fixture
def api_client():
    return TestClient(app)
