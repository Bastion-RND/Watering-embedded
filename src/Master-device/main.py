import machine
from machine import SPI, Pin
import uasyncio as asyncio
import usocket as socket
import ubinascii
import ujson

from pkg import MasterDevice
from LoRa import Lora

from micropython import const
from machine import UART, Pin
from network import WLAN, STA_IF
from lib.gsm.SIM800x import SIM800x
from lib.umqtt.client import MQTTClient, Logger


global master
master = MasterDevice()
period_time = const(10)

def connect() -> WLAN:
    sta_if = WLAN(STA_IF)

    if sta_if.active():
        sta_if.disconnect()
        sta_if.active(False)

    sta_if.active(True)
    sta_if.connect('KB2', 'Bast2021Ion')
    sta_if.nconect(True, False)

    while not sta_if.isconnected():
        pass

    print('WLAN connected:', sta_if.ifconfig())
    return sta_if

def on_mqtt_connected(event: str, **kwargs):
    _client: MQTTClient = kwargs.get('mqtt_client')
    print(f'MQTT Connected to {_client.host}:{_client.port}')

def on_mqtt_disconnected(event: str, **kwargs):
    _client: MQTTClient = kwargs.get('mqtt_client')
    _reason = kwargs.get('err', f'RC: {kwargs.get("return_code")}')
    print(f'MQTT Disconnected from {_client.host}:{_client.port}, {_reason}')

def on_mqtt_subscribed(event: str, **kwargs):
    _client: MQTTClient = kwargs.get('mqtt_client')
    for rc in kwargs.get('return_codes'):
        if rc == MQTTClient.SUBSCRIBE_RC_FAILURE:
            print(f'MQTT Subscribe failed...')
    print(f'MQTT Subscribe success!')

def on_mqtt_publish_received(event: str, **kwargs):
    _client: MQTTClient = kwargs.get('mqtt_client')
    _topic: str = kwargs.get('topic')
    _payload: bytes = kwargs.get('payload')
    global master
    topic_callback(master, _topic, _payload)
    print(f'MQTT received topic: "{_topic}", payload: {_payload}')

    if _topic.endswith('/req') and _payload.decode('utf8') == 'reboot':
        _client.publish(topic='status', payload='0', retain=True)
        _client.disconnect()

def on_sim800_event(event: str, **kwargs):
    print(f'SIM800 event: "{event}", {kwargs}')

def topic_callback(master, topic: str, payload: bytes):
    if topic == 'service/time/utc':
        master.lastTs = int(payload.decode('utf8'))
    if topic == f'FF09/{master.uuid}/req' and payload == b'true':
        master.req = True
    if topic == f'FF09/{master.uuid}/updated':
        payload = ujson.loads(payload.decode('utf8').replace("'", '"'))
        master.update(payload)
    if topic == f'FF09/{master.uuid}/add-wireless-sensor':
        payload = ujson.loads(payload.decode('utf8').replace("'", '"'))
        master.add_lora(payload.get("name"), payload.get("uid"))
    if topic == f'FF09/{master.uuid}/remove-wireless-sensor':
        payload = ujson.loads(payload.decode('utf8').replace("'", '"'))
        master.delete_lora(payload.get("uid"))
        
async def publish_pkg(master, mqtt, period_s):
    while True:
        mqtt.publish(topic=master.uuid, payload=master.convert_to_pkg(), retain=False)
        await asyncio.sleep(period_s)

async def lora_pkg(master, lora, period_s):
    while True:
        if lora.available() != 0:
            uid, hum, bat = lora.read()
            rssi = (lora.get_packet_status())// (-2)
            status = lora.get_status()
            if status != 9 or status != 8:
                print(f'LoRa packet receive: {uid}, {hum}, {bat}, {rssi}')
                master.lora_data(uid, hum, bat, rssi)
            else:
                print('LoRa packet error!')
        lora.get_irq_status()
        if lora.irq_state != 0:
            lora.callback()
        await asyncio.sleep(period_s)

async def check_outputs_value(master, period_s):
    while True:
        master.check_outputs_val()
        await asyncio.sleep(period_s)

async def check_schedule_value(master, period_s):
    while True:
        master.check_outputs_sch()
        await asyncio.sleep(period_s)

async def check_api(master, mqtt, period_s):
    while True:
        if master.req == True:   
            mqtt.publish(topic=master.uuid, payload=master.convert_to_pkg(), retain=False)
            mqtt.publish(topic=f'{master.uuid}/req', payload = b'false', retain=False)
            master.req = False
        await asyncio.sleep(period_s)

async def start():
    await asyncio.sleep(1)

    #wlan = connect() #for Wi-Fi connect
    sim800 = SIM800x(UART(2, 115200, rx=17, tx=18), log_level=Logger.WARNING)
    
    reset = Pin(10, Pin.OUT, Pin.PULL_UP)
    cs = Pin(11, Pin.OUT, Pin.PULL_UP)
    busy = Pin(9, Pin.IN, Pin.PULL_DOWN)
    dio1 = Pin(46, Pin.IN, Pin.PULL_UP)
    txen = Pin(48, Pin.OUT, Pin.PULL_DOWN)
    rxen = Pin(47, Pin.OUT, Pin.PULL_DOWN)
    
    spi = SPI(2, baudrate=4000000, sck=Pin(14, Pin.OUT, Pin.PULL_DOWN), mosi=Pin(13, Pin.OUT, Pin.PULL_DOWN),
              miso=Pin(12, Pin.IN, Pin.PULL_UP))
    spi.deinit()
    spi.init()
    
    lora = Lora(spi, cs, reset, busy, dio1, txen, rxen)

    master.output1.out = Pin(42, Pin.OUT, Pin.PULL_DOWN)
    master.output2.out = Pin(41, Pin.OUT, Pin.PULL_DOWN)
    master.output3.out = Pin(40, Pin.OUT, Pin.PULL_DOWN)
    master.output4.out = Pin(39, Pin.OUT, Pin.PULL_DOWN)

    for _event in SIM800x.EVENTS_LIST:
        sim800.append_callback(_event, on_sim800_event)

    await sim800.initialise()
    await sim800.ppp_connect()  

    mqtt = MQTTClient(log_level=Logger.WARNING)
    mqtt.append_callback(MQTTClient.EVENT_CONNECTED, on_mqtt_connected)
    mqtt.append_callback(MQTTClient.EVENT_DISCONNECTED, on_mqtt_disconnected)
    mqtt.append_callback(MQTTClient.EVENT_SUBSCRIBED, on_mqtt_subscribed)
    mqtt.append_callback(MQTTClient.EVENT_PUBLISH_RECEIVED, on_mqtt_publish_received)

    await mqtt.connect(
        host='t1.bast-dev.ru',
        keepalive_period=60,
         client_id='device::FF09',
    )

    _prefix = mqtt.client_id.lstrip('device::')
    mqtt.subscribe(topic=_prefix + '/api/+/req/#')
    mqtt.subscribe(topic='service/time/utc')
    mqtt.subscribe(topic=f'FF09/{master.uuid}/req')
    mqtt.subscribe(topic=f'FF09/{master.uuid}/updated')
    mqtt.subscribe(topic=f'FF09/{master.uuid}/add-wireless-sensor')
    mqtt.subscribe(topic=f'FF09/{master.uuid}/remove-wireless-sensor')
    
    mqtt.publish(topic=f'{master.uuid}/status',payload='1', retain=True)
  
    lora.begin()
    lora.set_frequency()
    lora.set_rx_gain()

    dio1.irq(trigger=Pin.IRQ_RISING, handler=lora.callback())
    dio1.irq
    lora.set_lora_modulation()
    lora.set_sync_word()
    lora.set_lora_packet()

    lora.request()

    asyncio.create_task(publish_pkg(master, mqtt, 900))
    asyncio.create_task(check_api(master, mqtt, 1))
    asyncio.create_task(lora_pkg(master, lora, 1))
    asyncio.create_task(check_outputs_value(master, 2))
    asyncio.create_task(check_schedule_value(master, 2))

    try:
        while mqtt.is_connected:
            await asyncio.sleep(1)

        await sim800.ppp_disconnect()

        print('ESP will be rebooted...')
        await asyncio.sleep(5)

        machine.reset()

    except KeyboardInterrupt:
        print('Program finished!')
        exit(0)

asyncio.run(start())
