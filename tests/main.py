import asyncio
import logging
from eidolon import Parallelizer
from eidolon.api_request import APIRequest

async def callback(request, response):
    print(response.status)
    print(await response.text())


req = APIRequest(
    task_id=1,
    attempts_left=2,
    request_method="GET",
    request_url="https://www.google.com",
    request_headers={"User-Agent": "Mozilla/5.0"},
    request_params={"q": "python"},
    request_json={"key": "value"},
    request_form_data={"key": "value"},
    callback=callback,
)

parra = Parallelizer(
    logging_level=logging.INFO, # default: logging.ERROR
    max_requests_per_second=10, # default: 1
    max_retry_attempts=1, # default: 3
    seconds_to_sleep_after_rate_limit_error=10, # default: 15
)
prom = parra.make_requests([req] * 100)

asyncio.run(prom)