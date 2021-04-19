import paho.mqtt.client as mqtt
import json
import time
import logging
from dotenv import dotenv_values

theClient = 0
LOGGER = logging.getLogger(__name__)

def on_connect(client, userdata, flags, rc):
    LOGGER.info("MQTT Client connection result: " + mqtt.connack_string(rc))

def on_disconnect(client, userdata, rc):
    if rc != 0:
        LOGGER.error("MQTT Client disconnected!")

def initializeClient():
    global theClient
    theClient = mqtt.Client("doughboy")
    config = dotenv_values(".env")
    theClient.username_pw_set(config["MQTT_USERNAME"], config["MQTT_PASSWORD"])
    theClient.on_connect = on_connect
    theClient.on_disconnect = on_disconnect
    theClient.connect("myvault.localdomain")
    theClient.loop_start()

def cleanup():
    global theClient
    if (theClient):
        theClient.loop_stop()

def publish(payloads):
    global theClient
    if (theClient == 0):
        initializeClient()
    
    theClient.publish("project/doughboy", payloads)
    
if __name__ == "__main__":

    LOGGER.info("testing mqtt client code - pushing a temp")
    payload = {"curTemp":70}
    publish(json.dumps(payload))

    LOGGER.info("sleeping 3 secs before cleanup")
    time.sleep(3)
    cleanup()
