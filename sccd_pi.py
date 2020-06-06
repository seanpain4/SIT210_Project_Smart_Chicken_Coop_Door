# Import libraries
import RPi.GPIO as GPIO
from datetime import datetime, time, timedelta
from time import sleep
import paho.mqtt.client as mqtt
from geopy.geocoders import Nominatim
import requests
import json

# Define variables
BEAM1 = 11
BEAM2 = 13
BEAM3 = 15
STEPPER = [16, 18, 22, 36]
stepperSeq = [[1,0,0,0],
              [1,1,0,0],
              [0,1,0,0],
              [0,1,1,0],
              [0,0,1,0],
              [0,0,1,1],
              [0,0,0,1],
              [1,0,0,1]]

# Default values
disableDoorToggle = False
chickenActivity = False
chickenTotal = 3
chickenInside = 3
doorLocation = "Melbourne, Victoria, Australia"
sunriseTime = datetime.now().time()
sunsetTime = datetime.now().time()

# ------ Define Functions ------

# Disable beam break detection - can choose to exclude a pin
def disableBeamBreak(exclude=None):
    if (exclude == None):
        GPIO.remove_event_detect(BEAM1)
        GPIO.remove_event_detect(BEAM2)
        GPIO.remove_event_detect(BEAM3)
    elif (exclude == BEAM1):    
        GPIO.remove_event_detect(BEAM2)
        GPIO.remove_event_detect(BEAM3)
    elif (exclude == BEAM2):
        GPIO.remove_event_detect(BEAM1)
        GPIO.remove_event_detect(BEAM3)
    elif (exclude == BEAM3):
        GPIO.remove_event_detect(BEAM1)
        GPIO.remove_event_detect(BEAM2)
    else:
        print("ERROR: Invalid beam.")

# Enable beam break detection - can choose to exclude a pin
def enableBeamBreak(exclude=None):
    if (exclude == None):
        GPIO.add_event_detect(BEAM1, GPIO.FALLING, callback=breakBeam)
        GPIO.add_event_detect(BEAM2, GPIO.FALLING, callback=breakBeam)
        GPIO.add_event_detect(BEAM3, GPIO.FALLING, callback=breakBeam)
    elif (exclude == BEAM1):    
        GPIO.add_event_detect(BEAM2, GPIO.FALLING, callback=breakBeam)
        GPIO.add_event_detect(BEAM3, GPIO.FALLING, callback=breakBeam)
    elif (exclude == BEAM2):
        GPIO.add_event_detect(BEAM1, GPIO.FALLING, callback=breakBeam)
        GPIO.add_event_detect(BEAM3, GPIO.FALLING, callback=breakBeam)
    elif (exclude == BEAM3):
        GPIO.add_event_detect(BEAM1, GPIO.FALLING, callback=breakBeam)
        GPIO.add_event_detect(BEAM2, GPIO.FALLING, callback=breakBeam)
    else:
        print("ERROR: Invalid beam.")


# Beam break callback function
def breakBeam(pin):
    if (pin == BEAM1 or pin == BEAM3):
        chickenMovement(pin)
    
    
# Chicken Movement Function - Triggered when movement in door 
def chickenMovement(pin):
    global chickenInside
    global chickenActivity
    # Stops door from opening or closing
    chickenActivity = True
    # Chicken going out
    if (pin == BEAM3):
        # Disable beam detect callback
        disableBeamBreak(BEAM3)
        timeout = datetime.now() + timedelta(seconds = 5)
        # Wait for pin to go down
        while GPIO.input(BEAM2):
            if (datetime.now() > timeout):
                print("Chicken didn't make it outside")
                break
        else:
            timeout = datetime.now() + timedelta(seconds = 5)
            # Wait for final pin to go down
            while GPIO.input(BEAM1):
                if (datetime.now() > timeout):
                    print("Chicken didn't make it outside")
                    break
            else:
                if (chickenInside == 0):
                    print("ERROR: Chicken count is wrong!")
                else:
                    print("Chicken went outside!")
                    chickenInside -= 1
        # Enable beam detect callback
        enableBeamBreak(BEAM3)
    # Chicken going in
    elif (pin == BEAM1):
        # Disable beam detect callback
        disableBeamBreak(BEAM1)
        timeout = datetime.now() + timedelta(seconds = 5)
        # Wait for pin to go down
        while GPIO.input(BEAM2):
            if (datetime.now() > timeout):
                print("Chicken didn't make it inside")
                break
        else:
            timeout = datetime.now() + timedelta(seconds = 5)
            # Wait for pin to go down
            while GPIO.input(BEAM3):
                if (datetime.now() > timeout):
                    print("Chicken didn't make it inside")
                    break
            else:
                if (chickenInside == chickenTotal):
                    print("ERROR: Chicken count is wrong!")
                else:
                    print("Chicken went inside!")
                    chickenInside += 1
        # Enable beam detect callback
        enableBeamBreak(BEAM1)
    print("Chickens inside:", chickenInside)
    chickenActivity = False
    

# Toggle door
def toggleDoor():
    global disableDoorToggle
    # Stop multiple threads running at same time
    if (disableDoorToggle):
        return
    disableDoorToggle = True
    # Disable door while chicken activity
    while (chickenActivity):
        pass
    sleep(0.5)
    # Disable all beams for door to move
    disableBeamBreak()
    # Check status of stepper pin to determine position (need a limit switch)
    if (GPIO.input(STEPPER[3])):
        # Door up
        for i in range(1216): # 1216 steps
            for halfstep in range(8): # Times by 8 half steps
                for pin in range(4): # Then set each pin position
                    GPIO.output(STEPPER[pin], stepperSeq[::-1][halfstep][pin])
                sleep(0.001)
    else:
        # Door down
        for i in range(1216): # 1216 steps
            for halfstep in range(8): # Times by 8 half steps
                for pin in range(4): # Then set each pin position
                    GPIO.output(STEPPER[pin], stepperSeq[halfstep][pin])
                sleep(0.001)
    # Enable beam break callbacks
    enableBeamBreak()
    # Allow door to be controled again
    disableDoorToggle = False


# Get sunset and sunrise times for location
def getSunTimes(lat, long):
    global sunriseTime, sunsetTime
    # Query API
    url = 'https://api.sunrise-sunset.org/json?lat='+str(lat)+'&lng='+str(long)+'&formatted=0'
    r = requests.get(url)
    data = json.loads(r.content)
    sunrise = data['results']['sunrise']
    sunset = data['results']['sunset']
    # Create time object from results
    sunriseTime = time(int(sunrise[11:13]), int(sunrise[14:16]), int(sunrise[17:19]))
    sunsetTime = time(int(sunset[11:13]), int(sunset[14:16]), int(sunrise[17:19]))
    
    
# MQTT On Connect Function
def mqttOnConnect(client, userdata, flags, rc):
    #print("Connected with result code "+str(rc))
    client.subscribe("SmartChickenCoop/cmd/#")
    client.subscribe("SmartChickenCoop/data/request")


# MQTT On Message Function
def mqttOnMessage(client, userdata, msg):
    print(msg.topic+" "+msg.payload.decode("utf-8"))


# MQTT Cmd Callback
def mqttCmdCallback(client, userdata, msg):
    # Toggle door callback option
    if (msg.topic == "SmartChickenCoop/cmd/door" and msg.payload.decode("utf-8") == "toggle"):
        toggleDoor()
    # Setting total chicken count callback option
    elif (msg.topic == "SmartChickenCoop/cmd/chickens/total"):
        global chickenTotal
        try:
            chickenTotal  = int(msg.payload.decode("utf-8"))
        except:
            print("ERROR: Payload contained invalid characters.")
        print("The total number of chickens is: " + str(chickenTotal))
    # Setting chicken inside count callback option
    elif (msg.topic == "SmartChickenCoop/cmd/chickens/inside"):
        global chickenInside
        try:
            chickenInside  = int(msg.payload.decode("utf-8"))
        except:
            print("ERROR: Payload contained invalid characters.")
        print("The number of chickens inside is: " + str(chickenInside))
    # Setting location callback option
    elif (msg.topic == "SmartChickenCoop/cmd/location"):
        global doorLocation
        # Use nominatim and geocode to lookup location input
        geolocator = Nominatim(user_agent="SmartChickenCoopDoor")
        location = geolocator.geocode(msg.payload.decode("utf-8"))
        doorLocation = location.address
        # Pass Lat and Long to sun time function to update those global vars
        getSunTimes(location.latitude, location.longitude)
    

# MQTT data request callback - returns updated data for the GUI
def mqttDataCallback(client, userdata, msg):
    if (msg.topic == "SmartChickenCoop/data/request"):
        if (msg.payload.decode("utf-8") == "request_first"):
            sleep(1)
        payload = str(chickenTotal) + "/" + str(chickenInside) + "/" + doorLocation + "/" + str(GPIO.input(STEPPER[3]))
        mqttClient.publish("SmartChickenCoop/data/update", payload) 

# ------ Begin Code ------

# MQTT SETUP
mqttClient = mqtt.Client("ChickenCoopRasPi")
mqttClient.on_connect = mqttOnConnect
mqttClient.on_message = mqttOnMessage
mqttClient.message_callback_add("SmartChickenCoop/cmd/#", mqttCmdCallback)
mqttClient.message_callback_add("SmartChickenCoop/data/request", mqttDataCallback)
mqttClient.connect("mqtt.eclipse.org", 1883)
mqttClient.loop_start()

# Set pin mode
GPIO.setmode(GPIO.BOARD)

# Beam pin setup
GPIO.setup(BEAM1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BEAM2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BEAM3, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Enable beam break detect
enableBeamBreak()

# Setup stepper pins
for pin in STEPPER:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, 0)

# Check time for door infinitely - auto opens or closes with the sun
while True:
    try:
        # Get UTC time now and compare with sunrise and sunset times
        currentUTCTimeRaw = datetime.utcnow()
        currentUTCTime = time(int(currentUTCTimeRaw.strftime("%H")), int(currentUTCTimeRaw.strftime("%M")), int(currentUTCTimeRaw.strftime("%S")))
        if sunriseTime < currentUTCTime < sunsetTime:
            # Triggers door if stepper state doesnt match (limit switch would help)
            if (not GPIO.input(STEPPER[3])):
                toggleDoor()
        elif sunsetTime < currentUTCTime < sunriseTime:
            if (GPIO.input(STEPPER[3])):
                toggleDoor()
        sleep(10)
    except:
        break


# End script

# Close MQTT
mqttClient.loop_stop()
mqttClient.disconnect()

# Close door when ending script
if (GPIO.input(STEPPER[3])):
    toggleDoor()
    
# Clean pins before closing
GPIO.cleanup()
