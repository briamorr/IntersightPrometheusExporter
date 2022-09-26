```python
import os
import time
from typing import Counter
from prometheus_client import start_http_server, Gauge, Enum
import json
import requests
import math
from datetime import date
from datetime import timedelta

from intersight_auth import IntersightAuth

class AppMetrics:
    """
    Representation of Prometheus metrics and loop to fetch and transform
    application metrics into Prometheus metrics.
    """

    def __init__(self, polling_interval_seconds=60):
        self.polling_interval_seconds = polling_interval_seconds

        # Prometheus metrics to collect
        label_names = ['serial']
        self.kwh = Gauge("sum_kwh", "Kilowatt hour",label_names)

    def run_metrics_loop(self):
        """Metrics fetching loop"""
        #Configure Intersight API token and start finding all devices affected by a security advisory        
        AUTH = IntersightAuth(
            secret_key_filename='SecretKey.txt',
            api_key_id='xxxx/yyy/zzzz'
            )
        
        while True:
            self.getXSeriesServers(AUTH)
            time.sleep(self.polling_interval_seconds)

    def getPowerStats(self,serial,AUTH):
        today = date.today()
        yesterday = today - timedelta(days = 1)

        payload = """{
        "queryType": "timeseries",
        "dataSource": "ucs_component_stat",
        "granularity": {
            "type": "period",
            "period": "PT48H",
            "timeZone": "America/Los_Angeles"
        },
        "intervals": [\"""""" + str(yesterday) + """/""" + str(today) + """"],
        "filter": {
            "type": "and",
            "fields": [{
                    "type": "selector",
                    "dimension": "serial",
                    "value": \"""" + serial +""""
                }, {
                    "type": "regex",
                    "dimension": "blade",
                    "pattern": "Blade"
                }
            ]
        },
        "aggregations": [{
                "fieldName": "sumPowerConsumed",
                "type": "doubleSum",
                "name": "sumPowerConsumed"
            }, {
                "fieldName": "count",
                "type": "longSum",
                "name": "count"
            }
        ]
    }
    """
        RESPONSE = requests.post(
            url="https://intersight.com/api/v1/telemetry/TimeSeries",
            auth=AUTH,
            data=payload
        )

        recordCount = RESPONSE.json()

        for r in recordCount:
            kwh = r["result"]["sumPowerConsumed"] / r["result"]["count"]
            self.kwh.labels(serial).set(kwh)
   
    def getXSeriesServers(self,AUTH):
        json_body = {
            "request_method": "GET",
            "resource_path": (
                    "https://intersight.com/api/v1/compute/PhysicalSummaries?$filter=Model eq 'UCSX-210C-M6'"
            )
        }

        RESPONSE = requests.request(
            method=json_body['request_method'],
            url=json_body['resource_path'],
            auth=AUTH
        )

        recordCount = RESPONSE.json()["Results"]

        for r in recordCount:
            self.getPowerStats(r["Serial"],AUTH)

def main():
    """Main entry point"""

    polling_interval_seconds = int(os.getenv("POLLING_INTERVAL_SECONDS", "600"))
    exporter_port = int(os.getenv("EXPORTER_PORT", "9877"))

    app_metrics = AppMetrics(polling_interval_seconds=polling_interval_seconds)

    start_http_server(exporter_port)
    app_metrics.run_metrics_loop()

if __name__ == "__main__":
    main()
```
