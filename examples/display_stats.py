import argparse
import asyncio

import aiohttp
from pysunsynkweb.model import get_plants
from pysunsynkweb.session import SunsynkwebSession


async def _main(options):
    session = SunsynkwebSession(
        aiohttp.ClientSession(), options.username, options.password
    )
    inst = await get_plants(session)
    await inst.update()
    print(inst)
    print(inst.acc_battery_charge)
    print("===")
    for plant in inst.plants:
        print(plant)
        print(plant.acc_battery_charge)
        for inverter in plant.inverters:
            print("id| V . |  A    | W")
            for string in inverter.pv_strings.values():
                print(
                    " ",
                    string.id,
                    " ",
                    string.voltage,
                    string.amperage,
                    string.pv_power,
                )


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("username")
    argparser.add_argument("password")
    options = argparser.parse_args()
    asyncio.run(_main(options))
