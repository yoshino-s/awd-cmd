from typing import Any
from core.storage import Storage
from model.traffic import Traffic


storage = Storage(
    base_url="http://admin:Complexpass%23123@localhost:4080/"
)


def process_record(record: Any):
    record['request_body'] = record['request']
    record['request_ip'] = record['ip']
    record['request_port'] = record['port']
    record['response_headers'] = {
        a: b for a, b in [i.split(":", 1) for i in record['response_headers']]
    }
    traffic = Traffic(**record)
    id = traffic.machine + "_" + traffic.time.isoformat()
    storage.save(id, traffic).json()
