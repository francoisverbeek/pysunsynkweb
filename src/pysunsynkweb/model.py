"""Top level data model for the sunsynk web api."""

from dataclasses import dataclass, field
import decimal
import logging
import pprint
from typing import List, Union

from pysunsynkweb.inverter import Inverter

from .const import BASE_API
from .session import SunsynkwebSession

_LOGGER = logging.getLogger(__name__)


class Aggregated:
    @property
    def agg_collection(self):
        """The collection over which to aggregate"""
        raise NotImplementedError

    @property
    def acc_pv(self):
        """Accumulated energy from PV"""
        return sum(i.acc_pv for i in self.agg_collection)

    @property
    def acc_grid_export(self):
        return max(i.acc_grid_export for i in self.agg_collection)

    @property
    def acc_grid_import(self):
        return max(i.acc_grid_import for i in self.agg_collection)

    @property
    def acc_battery_discharge(self):
        return sum(i.acc_battery_discharge for i in self.agg_collection)

    @property
    def acc_battery_charge(self):
        return sum(i.acc_battery_charge for i in self.agg_collection)

    @property
    def acc_load(self):
        return sum(i.acc_load for i in self.agg_collection)


@dataclass
class Plant(Aggregated):
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
    session: Union[SunsynkwebSession, None] = None
    inverters: List[Inverter] = field(default_factory=list)

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
        self.inverters = [
            Inverter(k["sn"], session=self.session) for k in returned["data"]["infos"]
        ]

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

    async def update(self):
        """Update all sensors."""
        await self._get_instantaneous_data()
        for inverter in self.inverters:
            await inverter.update()

    @property
    def agg_collection(self):
        return self.inverters


@dataclass
class Installation(Aggregated):
    """An installation is a series of plants.

    This integration presents the plants as a single entity.
    """

    plants: List[Plant]

    @classmethod
    def from_api(cls, api_return, session):
        """Create the installation from the sunsynk web api."""
        assert "data" in api_return
        assert api_return["msg"] == "Success"
        return cls(
            plants=[Plant.from_api(ret, session) for ret in api_return["data"]["infos"]]
        )

    async def update(self):
        """Update all the plants. They will in turn update their sensors."""
        for plant in self.plants:
            await plant.update()

    @property
    def agg_collection(self):
        return self.plants


async def get_plants(session: SunsynkwebSession):
    """Start walking the plant composition."""
    returned = await session.get(BASE_API + "/plants", params={"page": 1, "limit": 20})
    installation = Installation.from_api(returned, session)
    for plant in installation.plants:
        await plant.enrich_inverters()
    return installation
