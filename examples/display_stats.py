import argparse
import asyncio

import aiohttp
from pysunsynkweb.model import  get_plants
from pysunsynkweb.session import SunsynkwebSession


async def _main(options):
    session = SunsynkwebSession(aiohttp.ClientSession(), options.username, options.password)
    inst = await get_plants(session)
    await inst.update()
    for plant in inst.plants:
        print(plant)

if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument('username')
    argparser.add_argument('password')
    options = argparser.parse_args()
    asyncio.run(_main(options))