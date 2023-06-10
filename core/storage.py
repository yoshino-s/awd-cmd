from datetime import datetime
import logging

import httpx
from verboselogs import VerboseLogger as getLogger

from model.traffic import Traffic

logging.getLogger('httpx').setLevel(logging.WARN)


class Storage(httpx.Client):
    logger = getLogger("db")

    def save(self, id, traffic: Traffic):
        self.logger.verbose(f"Saving {id}")
        data = traffic.dict()
        date: datetime = data['time']
        data['@timestamp'] = date.isoformat(timespec="seconds")
        del data['time']
        return self.put(f"/api/traffic/_doc/{id}", json=data)

    def drop(self, id: str):
        self.logger.verbose(f"Deleting {id}")
        return self.delete(f"/api/traffic/_doc/{id}")

    def exist(self, id: str):
        self.logger.verbose(f"Checking {id}")
        r = self.head(f"/api/traffic/_doc/{id}")
        return r.status_code == 200
