from dataclasses import dataclass
import datetime
import decimal


@dataclass
class PVString:
    """A PV 'string'.

    PV 'strings' are cables from a set of solar panels. Typically, your
    installer will group the panels on string based on common orientation
    or exposure to the sun.

    """

    id: int
    pv_voltage: decimal.Decimal = decimal.Decimal(0)
    pv_power: decimal.Decimal = decimal.Decimal(0)
    amperage: decimal.Decimal = decimal.Decimal(0)
    last_update: datetime.datetime = None

    def update_from_inv(self, data):
        """Update from invertor 'input' request.

                ```
                {
                        "id": null,
                        "pvNo": 1,
                        "vpv": "212.9",
                        "ipv": "1.0",
                        "ppv": "222.0",
                        "todayPv": "0.0",
                        "sn": "2211166856",
                        "time": "2024-06-13 07:54:05"
                    },
        ```
        """
        self.last_update = datetime.datetime.strptime(data["time"], "%Y-%m-%d %H:%M:%S")
        self.pv_power = decimal.Decimal(data["ppv"])
        self.voltage = decimal.Decimal(data["vpv"])
        self.amperage = decimal.Decimal(data["ipv"])
