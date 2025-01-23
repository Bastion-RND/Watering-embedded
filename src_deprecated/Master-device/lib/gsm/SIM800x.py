import utime as time
import uasyncio as asyncio

from micropython import const
from machine import Pin, UART
from network import PPP

from lib.uasync import AsyncTask, Logger

""" Constants """
_DEFAULT_TIMEOUT = const(5000)
_DEFAULT_POSTFIX = const('\r\n')

_RESULT_OK = const('OK')
_RESULT_ERROR = const('ERROR')
_RESULT_EXTENDED_ERROR = const('+CME ERROR:')


class GSMError(Exception):
    pass


class SIM800x(AsyncTask):
    EVENT_AT_COMMAND = const('at_command')
    EVENT_PROCEED_INCOMING = const('proceed_incoming')
    EVENT_GSM_REGISTERED = const('gsm_registered')
    EVENT_GPRS_ATTACHED = const('gprs_attached')
    EVENT_PPP_CONNECTED = const('ppp_connected')
    EVENT_PPP_DISCONNECTED = const('ppp_disconnected')
    EVENTS_LIST = [
        EVENT_AT_COMMAND,
        EVENT_PROCEED_INCOMING,
        EVENT_GSM_REGISTERED,
        EVENT_GPRS_ATTACHED,
        EVENT_PPP_CONNECTED,
        EVENT_PPP_DISCONNECTED,
    ]
    _callbacks: dict[str, set[callable]] = {}

    _modem: PPP = None
    _pin_reset: Pin = None

    _sim_card_ready: bool
    _gsm_registered: int
    _gprs_attached: int

    def __init__(self, serial: UART, gpio_rst: int = None, **kwargs):
        if 'name' not in kwargs.keys():
            kwargs['name'] = __class__.__name__

        AsyncTask.__init__(self, **kwargs)
        self.log.level = kwargs.get('log_level', Logger.TRACE)

        assert serial is not None, 'UART device is mandatory!'
        self._serial = serial

        if gpio_rst is not None:
            self._pin_reset = Pin(gpio_rst, Pin.OUT, value=1)

        for event in SIM800x.EVENTS_LIST:
            self._callbacks[event] = set()

        self._send_lock = asyncio.Lock()
        self._recv_lock = asyncio.Lock()
        self._loop_lock = asyncio.Lock()
        self._connect = asyncio.Lock()

        self._sim_card_ready = False
        self._gsm_registered = -1
        self._gprs_attached = -1

    def _emit_event(self, event: str, payload: dict):
        assert event in self.EVENTS_LIST
        payload = payload or dict()
        payload.update({'instance': self})
        for cb in self._callbacks[event]:
            cb(event, **payload)

    async def _send(self, s: str):
        _data = (s + _DEFAULT_POSTFIX).encode()
        await self._send_lock.acquire()
        self._serial.write(_data)
        self._send_lock.release()
        self.log.trace(f'[{time.ticks_ms():08d}] >> {_data}')

    async def _recv(self) -> str | None:
        await self._recv_lock.acquire()
        _data = self._serial.readline()
        self._recv_lock.release()
        if _data and len(_data):
            self.log.trace(f'[{time.ticks_ms():08d}] << {_data}')
            try:
                return _data.rstrip(b'\r\n\0\xFF').decode()
            except UnicodeError:
                pass  # raw bytes received...
        return None

    async def _proceed(self, received: str):
        if received.startswith('+CPIN:'):
            self._sim_card_ready = received.split(' ')[1] == 'READY'
            self.log.debug(f'Sim Card: {self.is_sim_card_ready}')

        elif received.startswith('+CREG:'):
            self._gsm_registered = int(received[7])
            self.log.debug(f'GSM: {self._gsm_registered}')
            self._emit_event(SIM800x.EVENT_GSM_REGISTERED, {'received': received})

        elif received.startswith('+CGATT:'):
            self._gprs_attached = int(received[8])
            self.log.debug(f'GPRS: {self._gprs_attached}')
            self._emit_event(SIM800x.EVENT_GPRS_ATTACHED, {'received': received})

        elif received == 'CONNECT':
            await self._connect.acquire()
            self.log.debug('CONNECTED!')
            self._emit_event(SIM800x.EVENT_PPP_CONNECTED, {'received': received})

        elif received == 'NO CARRIER':
            self.log.debug('DISCONNECTED...')
            self._emit_event(SIM800x.EVENT_PPP_DISCONNECTED, {'received': received})

        else:
            self.log.warning(f'Not implemented: "{received}"')
            self._emit_event(SIM800x.EVENT_PROCEED_INCOMING, {'received': received})

    async def _loop(self):
        if self._connect.locked():
            return

        if not self._loop_lock.locked():
            await self._loop_lock.acquire()

            if _str := await self._recv():
                await self._proceed(_str)

            self._loop_lock.release()

    async def _at(self, command: str = None, **kwargs) -> tuple[str, dict]:
        _prefix = kwargs.get('prefix', 'AT')
        _timeout = kwargs.get('timeout', _DEFAULT_TIMEOUT)
        _expected = kwargs.get('expected', '_DEADBEEF_')

        _cmd = _prefix or ''
        _cmd += '+' if _prefix and command else ''
        _cmd += command if command is not None else ''

        _ret = {'command': _cmd, 'return': []}
        _res = None

        await self._loop_lock.acquire()
        await self._send(_cmd)

        if _timeout:
            _ts = time.ticks_ms()
        else:
            _res = _RESULT_OK
            _ts = 0

        while _res is None:
            _now = time.ticks_ms()
            if time.ticks_diff(_now, _ts) >= _timeout:
                _res = _RESULT_ERROR + ': Timeout'
                break

            _str = await self._recv()

            if _str is None or _str == '' or _str == _cmd:
                continue  # skip timeout, empty lines, command echo

            elif (_str == _RESULT_OK) or _str.startswith(_expected):
                _res = _RESULT_OK
                _ret['return'].append(_str)

            elif (_str == _RESULT_ERROR) or _str.startswith(_RESULT_EXTENDED_ERROR):
                _res = _RESULT_ERROR
                _ret['return'].append(_str)

            elif _str.startswith('+') or _str in ['RDY', 'Call Ready', 'SMS Ready']:
                await self._proceed(_str)

            else:
                _ret['return'].append(_str)

            await asyncio.sleep_ms(0)  # NOTE: While must not block!

        self._loop_lock.release()

        if _res != _RESULT_OK:
            self.log.warning(f'Command "{_cmd}": {_res}')

        return _res, _ret

    async def _cmd(self, command: str = None, **kwargs) -> tuple[str, dict]:
        _attempts = kwargs.get('attempts')
        _interval = kwargs.get('interval', 1000)

        _res = None
        _ret = dict()

        if _attempts is not None:
            for _ in range(_attempts):
                _res, _ret = await self._at(command, **kwargs)
                if _res == _RESULT_OK:
                    break
                else:
                    _res = _RESULT_ERROR + ': MAX attempts'
                    _ret = {'command': command, 'return': []}
                await asyncio.sleep_ms(_interval)
        else:
            _res, _ret = await self._at(command, **kwargs)

        self._emit_event(SIM800x.EVENT_AT_COMMAND, _ret | {'result': _res})
        return _res, _ret

    async def _check_module(self, max_attempts=10) -> str:
        _res, _ = await self._cmd(command='AT', prefix=None, attempts=max_attempts)
        return _res

    def append_callback(self, event: str, cb: callable):
        assert event in self.EVENTS_LIST
        self._callbacks[event].add(cb)

    def remove_callback(self, event: str, cb: callable):
        assert event in self.EVENTS_LIST
        self._callbacks[event].remove(cb)

    async def initialise(self, max_attempts=10):
        self._sim_card_ready = False
        self._gsm_registered = -1
        self._gprs_attached = -1

        await self.reset()

        _res = await self._check_module()
        assert _res == _RESULT_OK, 'GSM Module does not response!'

        await asyncio.sleep_ms(5_000)

        # 2.2.7 ATE Set Command Echo Mode (and save state)
        await self._cmd('ATE0', prefix='')

        # 3.2.20 AT+CMEE Report Mobile Equipment Error, Set verbose
        _res, _ = await self._cmd('CMEE=2')
        assert _res == _RESULT_OK, 'Set "+CME ERROR:" verbose failed!'

        # 3.2.28 AT+CPIN Enter PIN, Read
        if not self.is_sim_card_ready:
            _res, _ = await self._cmd('CPIN?', attempts=10, interval=3_000)
            assert _res == _RESULT_OK, 'Sim card failure!'

        # 3.2.32 AT+CREG Network Registration
        while not self.is_gsm_registered:
            _res, _ = await self._cmd('CREG=1')
            assert _res == _RESULT_OK, 'Network Registration failed!'
            _res, _ = await self._cmd('CREG?')
            assert _res == _RESULT_OK, 'Network Registration failed!'

            if not self.is_gsm_registered:
                await asyncio.sleep_ms(5_000)

        # 4.2.8 AT+CNMI New SMS Message Indications, Disable
        _res, _ret = await self._cmd('CNMI=0,0,0,0,0')
        assert _res == _RESULT_OK, 'SMS Indications Disable failed!'

        # 6.2.45 AT+GSMBUSY Reject Incoming Call
        _res, _ret = await self._cmd('GSMBUSY=1')
        assert _res == _RESULT_OK, 'Incoming Call Disable failed!'

        # 7.2.1 AT+CGATT Attach to GPRS Service
        while not self.is_gprs_attached:
            # _res, _ = await self._cmd('CGATT=1')
            # assert _res == _AT_RESULT_OK, 'Attach GPRS Service failed!'
            _res, _ = await self._cmd('CGATT?', timeout=10_000)
            assert _res == _RESULT_OK, 'Attach GPRS Service failed!'

            if not self.is_gprs_attached:
                await asyncio.sleep_ms(5_000)

    async def info(self) -> dict[str, str]:
        if self._modem is not None and self._modem.active:
            raise GSMError('PPP is active!')

        _res = await self._check_module()
        assert _res == _RESULT_OK, 'GSM Module does not response!'

        # info = {
        #     # 2.2.34 AT+GMI Request Manufacturer Identification
        #     'manufacturer': (await self.command('GMI'))[1],
        #
        #     # 2.2.35 AT+GMM Request TA Model Identification
        #     'model': (await self.command('GMM'))[1],
        #
        #     # 2.2.36 AT+GMR Request TA Revision Identification of Software Release
        #     'revision': (await self.command('GMR'))[1],
        #
        #     # 2.2.38 AT+GSN Request TA Serial Number Identification (IMEI)
        #     'IMEI': (await self.command('GSN'))[1],
        # }
        return {}  # info

    async def reset(self):
        if self._modem is not None and self._modem.active:
            await self.ppp_disconnect()

        if self._pin_reset is not None:
            self._pin_reset.value(0)
            await asyncio.sleep_ms(100)
            self._pin_reset.value(1)
        else:
            _res, _ = await self._cmd('CFUN=1,1', timeout=5_000)
            assert _res == _RESULT_OK, 'Can`t reset module!'

    async def ppp_connect(self, apn='CMNET'):
        if not (self.is_gsm_registered and self.is_gprs_attached):
            raise GSMError('Network is not available!')

        # 7.2.2 AT+CGDCONT Define PDP Context
        res, _ = await self._cmd('CGDCONT=1,"IP","{}"'.format(apn))
        assert res == _RESULT_OK, 'Configure PDP Context failed!'

        # 7.2.6 AT+CGDATA Enter Data State, Point to Point protocol
        await self._cmd('CGDATA="PPP",1', timeout=0)

        """ CONNECT variant: dial """
        # await self._cmd('ATD*99#', prefix=None, timeout=0)

        while not self._connect.locked():
            await asyncio.sleep_ms(0)

        self._modem = PPP(self._serial)
        self._modem.active(True)

        while not self._modem.active():
            await asyncio.sleep_ms(0)

        self._modem.connect()

        while not self._modem.isconnected():
            await asyncio.sleep_ms(0)

    async def ppp_disconnect(self):
        if self._modem is not None:
            self._modem.active(False)

        # 2.2.12 +++ Switch from Data Mode or PPP Online Mode to Command Mode
        await asyncio.sleep_ms(1000)  # No characters entered for T1 time (1 second)
        await self._cmd('+++', prefix=None, timeout=0)
        await asyncio.sleep_ms(1000)  # No characters entered for T1 time (1 second)

        self._connect.release()

    @property
    def is_sim_card_ready(self) -> bool:
        return self._sim_card_ready

    @property
    def is_gsm_registered(self) -> bool:
        return self._gsm_registered == 1

    @property
    def is_gprs_attached(self) -> bool:
        return self._gprs_attached == 1
