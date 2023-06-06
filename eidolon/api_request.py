import asyncio
from dataclasses import dataclass, field
import inspect
import logging
import time
from typing import Callable, Dict, Literal
import aiohttp
from yarl import URL

from eidolon.tracker import StatusTracker


@dataclass
class APIRequest:
    """Stores an API request's inputs, outputs, and other metadata. Contains a method to make an API call."""

    task_id: int
    attempts_left: int
    result: list = field(default_factory=list)
    callback: Callable[[dict, dict], None] = None
    request_method: Literal[
        "GET", "POST", "HEAD", "PUT", "DELETE", "CONNECT", "OPTIONS", "TRACE", "PATCH"
    ] = None
    request_headers: Dict[str, str] | None = None
    request_json: dict | None = None
    request_params: dict | None = None
    request_form_data: aiohttp.FormData | dict | bytes | None = None
    request_url: str | URL = None

    async def call_api(
        self,
        retry_queue: asyncio.Queue,
        status_tracker: StatusTracker,
    ):
        """Calls the API and saves results."""
        logging.info(f"Starting request #{self.task_id}")
        error = None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=self.request_method,
                    url=self.request_url,
                ) as response:
                    if response.status == 429:
                        logging.warning(
                            f"Request {self.task_id} failed with status 429"
                        )
                        status_tracker.num_rate_limit_errors += 1
                        status_tracker.time_of_last_rate_limit_error = time.time()
                        error = True
                    
                    if error:
                        self.result.append(error)
                        if self.attempts_left:
                            retry_queue.put_nowait(self)
                        else:
                            logging.error(f"Request {self.request_json} failed after all attempts.")

                            status_tracker.num_tasks_in_progress -= 1
                            status_tracker.num_tasks_failed += 1
                    else:
                        try:
                            if inspect.iscoroutinefunction(self.callback):
                                await self.callback(self.request_json, response)
                            else:
                                logging.warn("Callback is not an async function")
                        except Exception as e:
                            logging.error(f"Callback for request {self.task_id} failed with Exception {e}")
                            pass

                        status_tracker.num_tasks_in_progress -= 1
                        status_tracker.num_tasks_succeeded += 1
                        logging.debug(f"Request {self.task_id} complete.")

        except (
            Exception
        ) as e:  # catching naked exceptions is bad practice, but in this case we'll log them
            logging.warning(f"Request {self.task_id} failed with Exception {e}")
            status_tracker.num_other_errors += 1
            error = e
