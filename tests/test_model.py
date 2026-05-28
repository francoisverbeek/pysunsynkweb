"""Tests of basic model and api interaction."""


# from tests.common import MockConfigEntry

import decimal

import aioresponses
from pysunsynkweb.client import SunsynkClient
from pysunsynkweb.model import get_plants
from tests.conftest import populatemocked
from decimal import Decimal

async def test_base_model():
    """Load the model and run one update"""
    with aioresponses.aioresponses() as mocked:
        populatemocked(mocked)
        session = SunsynkClient("testuser", "testpassword")
        installation = await get_plants(session)
        await installation.update()
        plant1, plant2 = installation.plants
        assert plant1.battery_power == -0.001
        assert plant2.battery_power == .001, "sign of battery power changes"
        assert plant1.grid_power == -.004
        assert plant2.grid_power == .004
        assert plant1.acc_load == Decimal('.002')
        assert plant1.ismaster() is True
        assert plant1.inverters[0].pv_strings[1].voltage == decimal.Decimal("212.9")
        assert installation.acc_battery_charge == 4
        assert installation.acc_battery_discharge == 6
        assert installation.acc_grid_export == 4
        assert installation.acc_grid_import == 6
        assert installation.acc_load == Decimal('.004')
        assert installation.acc_pv == 6
