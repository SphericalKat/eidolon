
import asyncio
import logging
import time
from typing import Generator, Iterable
from eidolon.api_request import APIRequest

from eidolon.tracker import StatusTracker

def _task_id_generator_function():
    """Generate integers 0, 1, 2, and so on."""
    task_id = 0
    while True:
        yield task_id
        task_id += 1


class Parallelizer:
    max_requests_per_second: int = 1
    max_retry_attempts: int = 3
    seconds_to_sleep_after_rate_limit_error: int = 15
    logging_level: int = logging.ERROR

    # initialize trackers
    _queue_of_requests_to_retry: asyncio.Queue = asyncio.Queue()
    _status_tracker: StatusTracker = StatusTracker()
    _task_id_generator: Generator
    _next_request = None

    # initialize available capacity counts
    _available_request_capacity = max_requests_per_second
    _last_update_time = time.time()
    _not_finished = True

    def __init__(self, max_requests_per_second=1, max_retry_attempts=3, logging_level=logging.ERROR, seconds_to_sleep_after_rate_limit_error=15):
        super().__init__()
        self.max_requests_per_second = max_requests_per_second
        self.max_retry_attempts = max_retry_attempts
        self.logging_level = logging_level
        self.seconds_to_sleep_after_rate_limit_error = seconds_to_sleep_after_rate_limit_error
        self._task_id_generator = _task_id_generator_function()

        logging.basicConfig(level=logging_level)

        logging.info("Parallelizer initialized")

    async def make_requests(self, input_requests: Iterable[APIRequest]):
        requests = input_requests.__iter__()

        while True:
            if self._next_request is None:
                if not self._queue_of_requests_to_retry.empty():
                    self._next_request = self._queue_of_requests_to_retry.get_nowait()
                    logging.debug(f"Retrying request {self._next_request.task_id}")
                elif self._not_finished:
                    try:
                        self._next_request = next(requests)
                        self._next_request.task_id = next(self._task_id_generator)
                        self._status_tracker.num_tasks_started += 1
                        self._status_tracker.num_tasks_in_progress += 1
                        logging.debug(f"Starting request {self._next_request.task_id}")
                    except StopIteration:
                        logging.debug("No more requests to make")
                        self._not_finished = False
            
            # update available capacity
            current_time = time.time()
            seconds_since_last_update = current_time - self._last_update_time
            self._available_request_capacity = min(
                self._available_request_capacity + (seconds_since_last_update * self.max_requests_per_second),
                self.max_requests_per_second,
            )
            self._last_update_time = current_time

            # if sufficient capacity, make request
            if self._next_request is not None and self._available_request_capacity >= 1:
                # update counters
                self._available_request_capacity -= 1
                self._next_request.attempts_left -= 1

                # make request
                asyncio.create_task(
                    self._next_request.call_api(
                        self._queue_of_requests_to_retry,
                        self._status_tracker,
                    )
                )
                self._next_request = None # reset next request to empty

            # if all tasks are finished, break
            if self._status_tracker.num_tasks_in_progress == 0:
                break

            # main loop sleeps briefly to avoid busy waiting
            await asyncio.sleep(0.01)

            # if a rate limit error has occurred, sleep until the rate limit is reset
            seconds_since_rate_limit_error = (
                time.time() - self._status_tracker.time_of_last_rate_limit_error
            )
            if seconds_since_rate_limit_error < self.seconds_to_sleep_after_rate_limit_error:
                remaining_sleep_time = (
                    self.seconds_to_sleep_after_rate_limit_error - seconds_since_rate_limit_error)
                await asyncio.sleep(remaining_sleep_time)
                logging.warn(f"Sleeping for {time.ctime(self._status_tracker.time_of_last_rate_limit_error + self.seconds_to_pause_after_rate_limit_error)}")

        logging.info("Finished making requests")
        if self._status_tracker.num_tasks_failed > 0:
            logging.warn(f"Failed {self._status_tracker.num_tasks_failed} tasks")
        if self._status_tracker.num_rate_limit_errors > 0:
            logging.warn(f"Encountered {self._status_tracker.num_rate_limit_errors} rate limit errors. Consider lowering the number of requests per second.")
