import asyncio
import logging
from parallelizer import Parallelizer
from parallelizer.api_request import APIRequest

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

parra = Parallelizer(logging_level=logging.INFO, max_requests_per_second=10)
prom = parra.make_requests([req] * 100)

asyncio.run(prom)