### Sensor for the balkon
### Reads and sends the data from the DHT20 sensor and sends it to the raspberry pi
### Upload this file with the name main.py onto the Pico

from handle_sensor import DHT20_IOT
from machine import Pin, I2C


IP_MQTT_BROKER= "192.168.0.11"
WIFI_NAME = 'haifisch'
WIFI_KEY = '<Your Wifi Key>'
CLIENT_NAME = "pico"
LOCATION = "balkon"
SENSOR_NAME = "DHT20"

sensor = DHT20_IOT(client_name=CLIENT_NAME,
                           measurement_interval=5,
                           ip_mqtt_broker=IP_MQTT_BROKER,
                           wifi_name=WIFI_NAME,
                           wifi_key=WIFI_KEY)


while True:
    sensor.measure()
    sensor.send_msg(topic = f"{LOCATION};{SENSOR_NAME};rh,t,abs_hum",
                      message = sensor.last_measurement)
    sensor.sleep_with_wdt()
