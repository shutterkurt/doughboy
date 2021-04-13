import paho.mqtt.client as mqtt
import json
import time

theClient = 0

def on_connect(client, userdata, flags, rc):
    print("MQTT Client connection result: " + mqtt.connack_string(rc))

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("MQTT Client disconnected!")

def initializeClient():
    global theClient
    theClient = mqtt.Client("doughboy")
    theClient.username_pw_set("someusername", "somepassword")
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

    print("testing mqtt client code - pushing a temp")
    payload = {"curTemp":70}
    publish(json.dumps(payload))

    print("sleeping 3 secs before cleanup")
    time.sleep(3)
    cleanup()
