import uasyncio as asyncio

from lib.uasync.logger import Logger


class AsyncTask:
    def __init__(self, **kwargs):
        self.log = Logger(
            name=kwargs.get('name', 'UNNAMED task'),
            level=kwargs.get('log_level', Logger.DEBUG)
        )

        self._sig_term = asyncio.Event()
        self._sig_pause = asyncio.Event()

        asyncio.create_task(self._task())

    def stop(self):
        self._sig_term.set()

    @property
    def is_stopped(self) -> bool:
        return self._sig_term.is_set()

    @property
    def pause(self) -> bool:
        return self._sig_pause.is_set()

    @pause.setter
    def pause(self, state: bool):
        if state:
            self._sig_pause.clear()
        else:
            self._sig_pause.set()

    async def _task(self):
        if self.log.name is not None:
            self.log.info('Started!')
        while not self.is_stopped:
            if not self.pause:
                # try:
                await self._loop()
                # except Exception as e:
                #     self.log.error(f'_loop exception: {str(e)}')

            await asyncio.sleep_ms(0)  # NOTE: While must not block!
        self.log.warning('Stopped')

    async def _loop(self):
        pass
