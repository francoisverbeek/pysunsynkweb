from dataclasses import dataclass, field
import decimal
from typing import Union
import copy
from pysunsynkweb.client import SunsynkClient
from pysunsynkweb.const import BASE_API
from pysunsynkweb.pvstring import PVString
from pysunsynkweb.settings_keys import SENDING_KEYS
import asyncio

@dataclass
class Inverter:
    sn: int
    session: Union[SunsynkClient, None] = None
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
    
    async def _get_settings(self):
        returned = await self.session.get(
            BASE_API + f'/common/setting/{self.sn}/read'
        )
        assert returned['success'], 'Request for current settings failed'
        return returned['data']

    async def _set_setting(self, name, value):
        original_settings = await self._get_settings()
        
        if name not in original_settings:
            raise RuntimeError(f'{name} not in original settings')
        sent_settings = {k: original_settings[k] for k in SENDING_KEYS}
        sent_settings[name] = value
        res = await self.session.post(
             BASE_API + f'/common/setting/{self.sn}/set', json=sent_settings
        )
        await asyncio.sleep(15)
        new_settings = await self._get_settings()
        return res, new_settings
        
    async def set_sell_mode(self):
        """Set inverter in export first."""
        return await self._set_setting('sysWorkMode', "0")
        
    async def set_battery_mode(self ):
        """Set inverter in load/battery first."""
        return await self._set_setting('sysWorkMode', "2")
        
        
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
        self.acc_load = decimal.Decimal(returned["data"]["totalUsed"]) /1000

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
