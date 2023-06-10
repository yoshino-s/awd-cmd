from datetime import datetime
from typing import Dict

import pydantic


class Traffic(pydantic.BaseModel):
    time: datetime
    machine: str
    headers: Dict[str, str]
    method: str
    protocol: str
    request_body: str
    request_ip: str
    request_port: str
    status_code: int
    response_headers: Dict[str, str]
    response: str

