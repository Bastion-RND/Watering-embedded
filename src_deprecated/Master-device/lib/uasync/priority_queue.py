# https://github.com/peterhinch/micropython-async/blob/master/v3/primitives/queue.py
# queue.py: adapted from uasyncio V2

# Copyright (c) 2018-2020 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

# Code is based on Paul Sokolovsky's work.
# This is sig_pin temporary solution until uasyncio V3 gets an efficient official version

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio


# Exception raised by get_nowait().
class QueueEmpty(Exception):
    pass


# Exception raised by put_nowait().
class QueueFull(Exception):
    pass


class PriorityQueueError(Exception):
    pass


class PriorityQueue:
    def __init__(self, max_size=1, max_priority=1):
        self._max_size = max_size
        self._max_priority = max_priority
        self._queue = [[] for _ in range(self._max_priority)]
        self._evput = asyncio.Event()  # Triggered by put, tested by get
        self._evget = asyncio.Event()  # Triggered by get, tested by put

    def get_nowait(self):
        self._evget.set()  # Schedule all tasks waiting on get
        self._evget.clear()
        for priority in range(self._max_priority):
            if len(self._queue[priority]):
                return self._queue[priority].pop(0)
        raise QueueEmpty()

    async def get(self):  # Usage: item = await queue.get()
        while 1:
            try:
                return self.get_nowait()
            except QueueEmpty:
                await self._evput.wait()

    def put_nowait(self, val, priority: int):
        if self.full(priority):
            raise QueueFull()
        self._evput.set()  # Schedule tasks waiting on put
        self._evput.clear()
        self._queue[priority].append(val)

    async def put(self, val, priority=0):  # Usage: await queue.put(item)
        while 1:
            try:
                return self.put_nowait(val, priority)
            except QueueFull:
                await self._evget.wait()

    def empty(self):  # Return True if the queue is empty, False otherwise.
        for priority in range(self._max_priority):
            if len(self._queue[priority]):
                return False
        return True

    def full(self, priority: int):  # Return True if there are maxsize items in the queue.
        if (priority < 0) or (priority >= len(self._queue)):
            raise PriorityQueueError('Wrong priority!')
        return self._max_size <= len(self._queue[priority])


# if __name__ == "__main__":
#     q = PriorityQueue(max_size=4, max_priority=2)
#     q.put_nowait(1, priority=1)
#     q.put_nowait(1, priority=1)
#     q.put_nowait(2, priority=1)
#     q.put_nowait('1234', priority=0)
#     q.put_nowait('12345678', priority=1)
#     print(q.get_nowait())
#     print(q.get_nowait())
#     print(q.get_nowait())
#     print(q.get_nowait())
#     print(q.get_nowait())
