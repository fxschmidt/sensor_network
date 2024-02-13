### Save the incoming data from the IOT sensors in the InfluxDB database
### Important tag is thereby the place of measurement

import numpy as np
import datetime as datetime
import paho.mqtt.client as mqtt
import paho.mqtt.subscribe as subscribe
import requests
from influxdb import DataFrameClient
from pandas import DataFrame

def send_telegram_message(message: str,who):
    """Sends a telegram message to Dana or Felix for special notifications

    Args:
        message (str): Content of the message
        who (str): Receiver of the message
    """
    if who == "felix":
        chat_id = "<Your Chat ID>"
    if who == "dana":
        chat_id = "<Your Chat ID2>"
    TOKEN = "<Your Telegram Token>"
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id}&text={message}&silent=true"
    print(requests.get(url).json()) # this sends the message

def message_to_database(client,userdata,message):
    """Store the incoming MQTT messages in the influxDB database. 
    Recap of the format: client = "pico_<place>"; topic = "<column1>,<column2>,..."; message = [50,20,6]

    Args:
        client (_type_): passed to the callback function - not necessary
        userdata (_type_): passed to the callback function - not necessary
        message (_type_): MQTT message
    """
    dt_now=datetime.datetime.now()
    message_content=message.payload.decode("utf-8")
    print(f"datetime now: {dt_now}")
    print(f"{message.topic = }")
    print(f"{message_content = }")
    
    #sending the telegram messages from the drawer controller
    if message.topic == "schublade":
        if message_content == "schublade geöfffnet":
            telegram_msg= "✅"
        else:
            telegram_msg = message_content #for testing purpose
        send_telegram_message(telegram_msg,who= "dana")
        send_telegram_message(telegram_msg,who= "felix")
        
        df = DataFrame(data = {"value":1},
                       index = [datetime.datetime.now(datetime.timezone.utc)])
        #save the action also in the database
        client_ifl.write_points(df,
            measurement = "schublade",
            tags = {"place":"Schublade",
                            "sensor":"Schubladen_Sensor"},
            time_precision = "s",
            numeric_precision = 2
            )
    else:
        try:
            #save the data from the different sensors in the influx database
            place = message.topic.split(";")[0]
            sensor_name = message.topic.split(";")[1]
            column_names = message.topic.split(";")[2]
            data = np.array(message_content.split(",")).reshape(1,-1).astype(np.float32)
            message_tag = {"place":place} #tags for each datapoint
            df = DataFrame(data = data,
                        columns = column_names.split(","),
                        index = [datetime.datetime.now(datetime.timezone.utc)])
            #adds the data from the sensors to the database
            client_ifl.write_points(df,
                measurement = sensor_name,
                tags = message_tag,
                time_precision = "s",
                numeric_precision = 2
                )
            print("saved to database")
        except: 
            print("Error: Couldn't store the data in the database")
   
#Establish database connection
client_ifl = DataFrameClient(database="IOT_at_home")

#Establish connection to the MQTT Client
client = mqtt.Client()

client.connect("192.168.0.11")
print("Ready to get messages")
#callback to process incoming messages from all topics 
subscribe.callback(message_to_database, "#") 
print("Running...")
