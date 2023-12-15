import machine
import uasyncio as asyncio
import usocket as socket
import ubinascii
import pkg
import ujson
from pkg import MasterDevice

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
        master.lastTs = payload
    if topic == f'P0PA/{master.uuid}/req' and payload == b'true':
        master.req = True
    if topic == f'P0PA/{master.uuid}/updated':
        payload = ujson.loads(payload.decode('utf8').replace("'", '"'))
        master.update(payload)
    if topic == f'P0PA/{master.uuid}/add-wireless-sensor':
        payload = ujson.loads(payload.decode('utf8').replace("'", '"'))
        master.add_lora(payload.get("name"), payload.get("uid"))
    if topic == f'P0PA/{master.uuid}/remove-wireless-sensor':
        payload = ujson.loads(payload.decode('utf8').replace("'", '"'))
        master.delete_lora(payload.get("uid"))
        
async def publish_pkg(master, mqtt, period_s):
    while True:
        mqtt.publish(topic=master.uuid, payload=master.convert_to_pkg(), retain=False)
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
         client_id='device::P0PA',
    )

    _prefix = mqtt.client_id.lstrip('device::')
    mqtt.subscribe(topic=_prefix + '/api/+/req/#')
    mqtt.subscribe(topic='service/time/utc')
    mqtt.subscribe(topic=f'P0PA/{master.uuid}/req')
    mqtt.subscribe(topic=f'P0PA/{master.uuid}/updated')
    mqtt.subscribe(topic=f'P0PA/{master.uuid}/add-wireless-sensor')
    mqtt.subscribe(topic=f'P0PA/{master.uuid}/remove-wireless-sensor')
    
    mqtt.publish(topic="status",payload='1', retain=True)
  
    asyncio.create_task(publish_pkg(master, mqtt, 900))
    asyncio.create_task(check_api(master, mqtt, 2))

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
