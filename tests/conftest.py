"""Common fixtures for the Sunsynk Inverter Web tests."""

import re

from sunsynk_web.const import BASE_API, BASE_URL


def populatemocked(mocked):
    """Return the normal start of coordinator minimal api required from the api."""
    mocked.post(BASE_URL + "/oauth/token", payload={"msg": "Success", "data": {"access_token": "12345"}})
    mocked.get(
        re.compile(BASE_API + "/plants.*"),
        payload={
            "msg": "Success",
            "data": {
                "infos": [
                    {"name": "plant1", "id": 1, "masterId": 1, "status": 0},
                    {"name": "plant2", "id": 2, "masterId": 1, "status": 0},
                ]
            },
        },
    )
    mocked.get(
        re.compile(BASE_API + r"/plant/\d/inverters.*"),
        payload={"msg": "Success", "data": {"infos": [{"sn": 123}]}},
        repeat=True,
    )
    mocked.get(
        re.compile(BASE_API + r"/plant/energy/\d/flow.*"),
        payload={
            "code": 200,
            "msg": "Success",
            "data": {
                "battPower": 1,
                "toBat": True,
                "soc": 2,
                "loadOrEpsPower": 3,
                "gridOrMeterPower": 4,
                "toGrid": True,
                "pvPower": 5,
            },
        },
    )
    mocked.get(
        re.compile(BASE_API + r"/plant/energy/\d/flow.*"),
        payload={
            "code": 200,
            "msg": "Success",
            "data": {
                "battPower": 1,
                "toBat": False,
                "soc": 2,
                "loadOrEpsPower": 3,
                "gridOrMeterPower": 4,
                "toGrid": False,
                "pvPower": 5,
            },
        },
    )
    mocked.get(
        re.compile(BASE_API + "/inverter/123/total.*"),
        repeat=True,
        # PV total
        payload={
            "data": {
                "infos": [
                    {
                        "records": [
                            {"year": 2024, "value": 1},
                            {"year": 2023, "value": 2},
                        ]
                    }
                ]
            }
        },
    )
    mocked.get(
        re.compile(BASE_API + "/inverter/grid/123/realtime.*"),
        payload={"data": {"etotalTo": 2, "etotalFrom": 3}},
        repeat=True,
    )
    mocked.get(
        re.compile(BASE_API + "/inverter/battery/123/realtime.*"),
        payload={"data": {"etotalChg": 2, "etotalDischg": 3}},
        repeat=True,
    )
    mocked.get(re.compile(BASE_API + "/inverter/load/123/realtime.*"), payload={"data": {"totalUsed": 2}}, repeat=True)
