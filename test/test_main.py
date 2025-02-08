import pytest
from src.main import json_checker
import sys


def test_detect_abscence_of_argument():
    response = json_checker()
    assert response == 'Please add a JSON argument'
