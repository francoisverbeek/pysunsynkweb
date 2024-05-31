"""Top level data model for the sunsynk web api."""

from dataclasses import dataclass
import decimal
import logging
import pprint
from typing import List, Union

from .const import BASE_API
from .session import SunsynkwebSession

_LOGGER = logging.getLogger(__name__)


@dataclass
class Plant:
    """Proxy for the 'Plant' object in sunsynk web api.

    A plant can host multiple inverters and other devices. Our plant object
    carries a summary of the data from all inverters in the plant.

    In the limited sample i've got, there is one plant per inverter.

    """

    id: int
    master_id: int
    name: str
    status: int
    battery_power: int = 0
    state_of_charge: float = 0
    load_power: int = 0
    grid_power: int = 0
    pv_power: int = 0
    inverter_sn: Union[int, None] = None
    acc_pv: decimal.Decimal = decimal.Decimal(0)
    acc_grid_export: decimal.Decimal = decimal.Decimal(0)
    acc_grid_import: decimal.Decimal = decimal.Decimal(0)
    acc_battery_discharge: decimal.Decimal = decimal.Decimal(0)
    acc_battery_charge: decimal.Decimal = decimal.Decimal(0)
    acc_load: decimal.Decimal = decimal.Decimal(0)
    session: Union[SunsynkwebSession , None] = None

    def __repr__(self):
        """Summary of the plant"""
        return f"""Plant {id}

        {self.name}
        Battery power {self.battery_power} W ({self.state_of_charge})%
        Grid Power: {self.grid_power} W
        PV Power: {self.pv_power} W
        Accumulated PV Energy {self.acc_pv} KWh
        Accumulated Grid export {self.acc_grid_export} KWh
        Accumulated Grid import {self.acc_grid_import} KWh
        Accumulated Load {self.acc_load} KWh
        Accumulated Battery discharge {self.acc_battery_discharge} KWh
        Accumulated Battery charge {self.acc_battery_charge} KWh

        """

    def ismaster(self):
        """Is the plant a master plant.

         Unused at the moment, but required when introducing read-write calls
        (for instance to command to charge batteries from the grid).
        """
        return self.master_id == self.id

    @classmethod
    def from_api(cls, api_return, session):
        """Create the plant from the return of the web api."""
        return cls(
            name=api_return["name"],
            id=api_return["id"],
            master_id=api_return["masterId"],
            status=api_return["status"],
            session=session,
        )

    async def enrich_inverters(self):
        """Populate inverters' serial numbers.

        The plant summary doesn't contain the inverters, so we have a
        separate call to populate inverter's serial numbers.
        """
        returned = await self.session.get(
            BASE_API + f"/plant/{self.id}/inverters",
            params={"page": 1, "limit": 20, "type": -1, "status": -1},
        )
        assert len(returned["data"]["infos"]) == 1
        self.inverter_sn = returned["data"]["infos"][0]["sn"]

    async def _get_instantaneous_data(self):
        """Populate instantaneous data.

        Instantaneous data is conveniently summarized in the 'flow' api end point.
        """
        returned = await self.session.get(
            BASE_API + f"/plant/energy/{self.id}/flow",
            params={"page": 1, "limit": 20},
        )
        _LOGGER.debug("Flow Api returned %s", pprint.pformat(returned))

        self.battery_power = returned["data"]["battPower"]
        if returned["data"]["toBat"]:
            self.battery_power *= -1
        self.state_of_charge = returned["data"]["soc"]
        self.load_power = returned["data"]["loadOrEpsPower"]
        self.grid_power = returned["data"]["gridOrMeterPower"]
        if returned["data"]["toGrid"]:
            self.grid_power *= -1
        self.pv_power = returned["data"]["pvPower"]

    async def _get_total_grid(self):
        returned = await self.session.get(
            BASE_API + f"/inverter/grid/{self.inverter_sn}/realtime",
            params={"lan": "en"},
        )
        self.acc_grid_export = returned["data"]["etotalTo"]
        self.acc_grid_import = returned["data"]["etotalFrom"]

    async def _get_total_battery(self):
        returned = await self.session.get(
            BASE_API + f"/inverter/battery/{self.inverter_sn}/realtime",
            params={"lan": "en"},
        )
        self.acc_battery_charge = returned["data"]["etotalChg"]
        self.acc_battery_discharge = returned["data"]["etotalDischg"]

    async def _get_total_pv(self):
        returned = await self.session.get(
            BASE_API + f"/inverter/{self.inverter_sn}/total",
            params={"lan": "en"},
        )
        self.acc_pv = sum([decimal.Decimal(i["value"]) for i in returned["data"]["infos"][0]["records"]])

    async def _get_total_load(self):
        returned = await self.session.get(
            BASE_API + f"/inverter/load/{self.inverter_sn}/realtime",
            params={"lan": "en"},
        )
        self.acc_load = returned["data"]["totalUsed"]

    async def update(self):
        """Update all sensors."""
        await self._get_instantaneous_data()
        await self._get_total_pv()
        await self._get_total_grid()
        await self._get_total_battery()
        await self._get_total_load()


@dataclass
class Installation:
    """An installation is a series of plants.

    This integration presents the plants as a single entity.
    """

    plants: List[Plant]

    @classmethod
    def from_api(cls, api_return, session):
        """Create the installation from the sunsynk web api."""
        assert "data" in api_return
        assert api_return["msg"] == "Success"
        return cls(plants=[Plant.from_api(ret, session) for ret in api_return["data"]["infos"]])

    async def update(self):
        """Update all the plants. They will in turn update their sensors."""
        for plant in self.plants:
            await plant.update()


async def get_plants(session: SunsynkwebSession):
    """Start walking the plant composition."""
    returned = await session.get(BASE_API + "/plants", params={"page": 1, "limit": 20})
    installation = Installation.from_api(returned, session)
    for plant in installation.plants:
        await plant.enrich_inverters()
    return installation
