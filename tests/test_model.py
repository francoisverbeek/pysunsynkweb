"""Tests of basic model and api interaction."""


# from tests.common import MockConfigEntry

import aiohttp
import aioresponses
from pysunsynkweb.model import get_plants
from pysunsynkweb.session import SunsynkwebSession

from tests.conftest import populatemocked


async def test_base_model():
    """Load the model and run one update"""
    with aioresponses.aioresponses() as mocked:
        populatemocked(mocked)
        session = SunsynkwebSession(aiohttp.ClientSession(), "testuser", "testpassword")
        installation = await get_plants(session)
        await installation.update()
        plant1, plant2 = installation.plants
        assert plant1.battery_power == -1
        assert plant2.battery_power == 1, "sign of battery power changes"
        assert plant1.grid_power == -4
        assert plant2.grid_power == 4
        assert plant1.acc_load == 2
        assert plant1.ismaster() is True
        assert "Grid Power:" in repr(plant1)
