## generic class to handle sensor output and send this to 
import network,time,math,gc
from machine import Pin, I2C, WDT,lightsleep, ADC
from umqtt.simple import MQTTClient
from dht20 import DHT20

def calc_abs_humidity(rh,t):
    """Calc. the absolute humidity according to the formula given here: https://carnotcycle.wordpress.com/2012/08/04/how-to-convert-relative-humidity-to-absolute-humidity/

    Args:
        rh (float): relative humidity in %
        t (float): temperature in °C

    Returns:
        float: absolute humidity in g/m³
    """
    denominator = 6.112 * math.exp((17.67*t)/(t+ 243.5)) * rh * 2.1674
    nominator = 273.15 + t
    return denominator/nominator


class IOT_Sensor():
    """ Generic parent class of an IOT sensor on a Rasperry Pico that send measurements via MQTT to a central device. A WatchdogTimer is included to recover from errors especially because of connectivity issues. Thus remember to feed the wdt at least every 8 seconds.
    """
    
    def __init__(self,
                 client_name: str,
                 measurement_interval: int,
                 ip_mqtt_broker: str,
                 wifi_name: str,
                 wifi_key: str):
        """Provide the parameters necessary for the connection via WiFi/MQTT to a broker. 

        Args:
            client_name (str): For the mqtt connection and is important for the database. Stick to the scheme "Pico_<place>" e.g. "Pico_balkon".
            measurement_interval (int): Interval between each measurements in minutes
            ip_mqtt_broker (str): ip adress of the mqtt broker (the device where Mosquitto is installed)
            wifi_name (str): wifi name of the local wifi
            wifi_key (str): key of your local wifi
        """
        self.client_name = client_name
        self.measurement_interval = measurement_interval
        self.ip_mqtt_broker = ip_mqtt_broker
        self.wifi_name = wifi_name
        self.wifi_key = wifi_key
        self.wdt=WDT(timeout=8000)
        self.last_measurement = [] #stores the latest sensor readings
    
    def establish_connection(self):
        self.wdt.feed()
        #establish the wifi connection
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.config(pm = 0xa11140)
        self.wlan.active(True)
        self.wlan.connect(self.wifi_name, self.wifi_key)
        # Wait for connect or fail
        n_wait = 10
        while n_wait > 0:
            self.wdt.feed()
            if self.wlan.isconnected() == True:
                print("wifi connection established")
                break
            n_wait -= 1
            time.sleep(1)
        #connect to mqtt client
        client_error_counter=0
        while True:
            self.wdt.feed()
            try:
                self.mqtt_conn = MQTTClient(self.client_name,
                                            self.ip_mqtt_broker,
                                            keepalive=45)
                self.mqtt_conn.connect()
                time.sleep(1)
                print('Connected to the MQTT Broker')
                return True
            except:
                print(f"Error client connection")
                client_error_counter +=1
                if client_error_counter >10: #if connection isn't possible
                    break

    def mqtt_disconnect(self):
        """Disconnect all connections to save energy"""
        self.wdt.feed()
        self.mqtt_conn.disconnect()
        self.wlan.disconnect()
        print("disconnected")
        
    def sleep_with_wdt(self):
        """Sleeping to save energy"""
        slept_duration = 0
        print("Enter sleeping...")
        while slept_duration < (self.measurement_interval*60 -5):
            lightsleep(6000)
            self.wdt.feed()
            slept_duration += 6
        print("... sleeping done.")
        gc.collect()#tidy the RAM
        
    def send_msg(self,topic,message):
        """Sends a message to the broker

        Args:
            topic (str): Label of the data sen in the message. Scheme: "<place>_<column1>,<column2>,..." e.g. "balkon;rh,t,abs_hum"
            message (list): Data of the measurements in a list e.g. [50,20,6]
        """
        broker_connection = self.establish_connection()
        if broker_connection:
            self.mqtt_conn.publish(topic,str(message)[1:-1])
            self.wdt.feed()
            print("All packages sent")
            self.mqtt_disconnect()
        else:
            print("Sending wasn't successful because no connection could be established")
            
        
        

class DHT20_IOT(IOT_Sensor):
    """Child class for the DHT20 sensor"""
    
    def __init__(self, 
                 client_name: str,
                 measurement_interval: int,
                 ip_mqtt_broker: str,
                 wifi_name: str,
                 wifi_key: str):
        """Provide the parameters necessary for the connection via WiFi/MQTT to a broker. 

        Args:
            client_name (str): For the mqtt connection and is important for the database. Stick to the scheme "pico_<place>" e.g. "pico_balkon".
            measurement_interval (int): Interval between each measurements in minutes
            ip_mqtt_broker (str): ip adress of the mqtt broker (the device where Mosquitto is installed)
            wifi_name (str): wifi name of the local wifi
            wifi_key (str): key of your local wifi
        """
        super().__init__(client_name, measurement_interval,
                         ip_mqtt_broker,wifi_name,wifi_key)
        i2c = I2C(0, sda=Pin(4), scl=Pin(5)) #establish i2c connection with the sensor
        self.sensor = DHT20(0x38, i2c) #init the sensor with the DHT20 libary

    
    def measure(self):
        """Measure the temperature,rel. humidity and calculate the absolute humidity. Sets this new measurements as last_measurement which could then be send with .send_msg(topic,self.last_measurement)"""
        raw_measurement = self.sensor.measurements #reads the actual sensor measurements
        rel_humidity = raw_measurement["rh"]
        temperature = raw_measurement["t"]
        abs_humidity = calc_abs_humidity(rh= rel_humidity,
                                         t=temperature)
        self.last_measurement = [rel_humidity,temperature,abs_humidity] 
        print(self.last_measurement)

class Photoresistor(IOT_Sensor):
    """Child class for a Photoresistor"""
    def __init__(self, 
                 client_name: str,
                 measurement_interval: int,
                 ip_mqtt_broker: str,
                 wifi_name: str,
                 wifi_key: str):
        """Provide the parameters necessary for the connection via WiFi/MQTT to a broker. 

        Args:
            client_name (str): For the mqtt connection and is important for the database. Stick to the scheme "pico_<place>" e.g. "pico_balkon".
            measurement_interval (int): Interval between each measurements in minutes
            ip_mqtt_broker (str): ip adress of the mqtt broker (the device where Mosquitto is installed)
            wifi_name (str): wifi name of the local wifi
            wifi_key (str): key of your local wifi
        """
        super().__init__(client_name, measurement_interval,
                         ip_mqtt_broker,wifi_name,wifi_key)
        self.sensor = ADC(2)
        
    def measure(self,duration_integration=20):
        """Measurement of the brightness (in %) as the resistance of a photoresistor. 

        Args:
            duration_integration (int, optional): Choose a longer duration for the integration to reduce the noise. Defaults to 20.
        """
        n_loops = int(duration_integration/0.1)
        mean_reading = 0
        for i in range(n_loops):
            self.wdt.feed()
            reading_percent=self.sensor.read_u16()/65535
            mean_reading += reading_percent/n_loops
            time.sleep(0.1)
        
        self.last_measurement = [mean_reading]
        print(self.last_measurement)