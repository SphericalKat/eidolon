# Eidolon
A utility to concurrently make HTTP requests, with an optional rate limit. Powered by asyncio and aiohttp.

## Installation
Install and update via [pip](https://pip.pypa.io/en/stable/getting-started/)
```bash
pip install --U eidolon
```

## A Simple Example
```py3
import asyncio
import logging
from eidolon import Parallelizer
from eidolon.api_request import APIRequest

"""
the callback should ideally be an async function, since methods
like .json or .text on the response are async
"""

async def callback(request, response):
    print(response.status)
    print(await response.text())

"""
Create an APIRequest object. Each object corresponds to a single request, and can take in an optional callback
Everything except request_method and request_url is optional
"""
req = APIRequest(
    request_method="GET",
    request_url="https://www.google.com",
    request_headers={"User-Agent": "Mozilla/5.0"},
    request_params={"q": "python"},
    request_json={"key": "value"},
    request_form_data={"key": "value"},
    callback=callback,
)

p = Parallelizer(
    logging_level=logging.INFO, # default: logging.ERROR
    max_requests_per_second=10, # default: 1
    max_retry_attempts=1, # default: 3
    seconds_to_sleep_after_rate_limit_error=10, # default: 15
)

# make 100 requests
asyncio.run(p.make_requests([req] * 100))
```