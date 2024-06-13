from dataclasses import dataclass, field
import decimal
from typing import Union

from pysunsynkweb.const import BASE_API
from pysunsynkweb.pvstring import PVString
from pysunsynkweb.session import SunsynkwebSession


@dataclass
class Inverter:
    sn: int
    session: Union[SunsynkwebSession, None] = None
    acc_pv: decimal.Decimal = decimal.Decimal(0)
    acc_grid_export: decimal.Decimal = decimal.Decimal(0)
    acc_grid_import: decimal.Decimal = decimal.Decimal(0)
    acc_battery_discharge: decimal.Decimal = decimal.Decimal(0)
    acc_battery_charge: decimal.Decimal = decimal.Decimal(0)
    acc_load: decimal.Decimal = decimal.Decimal(0)
    pv_strings: dict = field(default_factory=dict)

    async def _get_total_grid(self):
        returned = await self.session.get(
            BASE_API + f"/inverter/grid/{self.sn}/realtime",
            params={"lan": "en"},
        )
        self.acc_grid_export = decimal.Decimal(returned["data"]["etotalTo"])
        self.acc_grid_import = decimal.Decimal(returned["data"]["etotalFrom"])

    async def _get_total_battery(self):
        returned = await self.session.get(
            BASE_API + f"/inverter/battery/{self.sn}/realtime",
            params={"lan": "en"},
        )
        self.acc_battery_charge = decimal.Decimal(returned["data"]["etotalChg"])
        self.acc_battery_discharge = decimal.Decimal(returned["data"]["etotalDischg"])

    async def _get_total_pv(self):
        returned = await self.session.get(
            BASE_API + f"/inverter/{self.sn}/total",
            params={"lan": "en"},
        )
        self.acc_pv = sum(
            [
                decimal.Decimal(i["value"])
                for i in returned["data"]["infos"][0]["records"]
            ]
        )

    async def _get_total_load(self):
        returned = await self.session.get(
            BASE_API + f"/inverter/load/{self.sn}/realtime",
            params={"lan": "en"},
        )
        self.acc_load = decimal.Decimal(returned["data"]["totalUsed"])

    async def _update_strings(self):
        returned = await self.session.get(
            BASE_API + f"/inverter/{self.sn}/realtime/input"
        )
        strings_raw = returned["data"]["pvIV"]
        for string in strings_raw:
            self.pv_strings.setdefault(
                string["pvNo"], PVString(id=string["pvNo"])
            ).update_from_inv(string)

    async def update(self):
        await self._get_total_pv()
        await self._get_total_grid()
        await self._get_total_battery()
        await self._get_total_load()
        await self._update_strings()
