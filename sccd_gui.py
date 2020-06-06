# Import libraries
import paho.mqtt.client as mqtt
import tkinter as tk
import time


# MQTT On Connect Function
def mqttOnConnect(client, userdata, flags, rc):
    #print("Connected with result code "+str(rc))
    client.subscribe("SmartChickenCoop/data/update")


# MQTT On Message Function
def mqttOnMessage(client, userdata, msg):
    print(msg.topic+" "+msg.payload.decode("utf-8"))


# Requests updated data on startup
def updateDataRequest():
    mqttClient.publish("SmartChickenCoop/data/request", "request_first")


# Gets new data and populates into the GUI from callback
def updateData(client, userdata, msg):
    #print("%s %s" % (msg.topic, msg.payload.decode("utf-8")))
    vals = msg.payload.decode("utf-8").split("/")
    entChickenTotal.delete(0, tk.END)
    entChickenTotal.insert(0, vals[0])
    entChickenInside.delete(0, tk.END)
    entChickenInside.insert(0, vals[1])
    entSetLocation.delete(0, tk.END)
    entSetLocation.insert(0, vals[2])
    if vals[3] == "0":
        btnToggleDoor.configure(text="Open Door")
    elif vals[3] == "1":
        btnToggleDoor.configure(text="Close Door")
    btnToggleDoor['state'] = "normal"
    btnUpdateData['state'] = "normal"


# Send new data to RasPi
def submitData():
    btnUpdateData['state'] = "disabled"
    mqttClient.publish("SmartChickenCoop/cmd/chickens/total", entChickenTotal.get(), retain=True)
    mqttClient.publish("SmartChickenCoop/cmd/chickens/inside", entChickenInside.get(), retain=True)
    mqttClient.publish("SmartChickenCoop/cmd/location", entSetLocation.get(), retain=True)
    mqttClient.publish("SmartChickenCoop/data/request", "request")
    

# Send doggle door command to RasPi
def toggleDoor():
    btnToggleDoor['state'] = "disabled"
    mqttClient.publish("SmartChickenCoop/cmd/door", "toggle")
    mqttClient.publish("SmartChickenCoop/data/request", "request")


# Set-up the window
window = tk.Tk()
window.title("Smart Chicken Coop")
window.resizable(width=False, height=False)
frmMain = tk.Frame(master=window, width=500)

# Widgets for interface
lblChickenTotal = tk.Label(master=frmMain, text="Total Chickens: ")
lblChickenTotal.config(font=("Courier", 18))
entChickenTotal = tk.Entry(master=frmMain, width=5)
entChickenTotal.config(font=("Courier", 18))

lblChickenInside = tk.Label(master=frmMain, text="Chickens Inside: ")
lblChickenInside.config(font=("Courier", 18))
entChickenInside = tk.Entry(master=frmMain, width=5)
entChickenInside.config(font=("Courier", 18))

lblSetLocation = tk.Label(master=frmMain, text="Location:")
lblSetLocation.config(font=("Courier", 18))
entSetLocation = tk.Entry(master=frmMain, width=20)
entSetLocation.config(font=("Courier", 18))


# Button for submitting data
btnUpdateData = tk.Button(
    master=frmMain,
    text="Submit",
    command=submitData
)
btnUpdateData.config(font=("Courier", 18))

# Button for toggle door
btnToggleDoor = tk.Button(
    master=frmMain,
    text="Open Door",
    command=toggleDoor
)
btnToggleDoor.config(font=("Courier", 18))

# Disable buttons by default, get activated when new data populates
btnUpdateData['state'] = "disabled"
btnToggleDoor['state'] = "disabled"

# Set Grid layout
lblChickenTotal.grid(row=0, column=0, sticky="e", columnspan=3)
entChickenTotal.grid(row=0, column=3, padx = 5, pady = 10, sticky="w")
lblChickenInside.grid(row=1, column=0, sticky="e", columnspan=3)
entChickenInside.grid(row=1, column=3, padx = 5, pady = 10, sticky="w")
lblSetLocation.grid(row=2, column=0, columnspan=4, pady = 10)
entSetLocation.grid(row=3, column=0, padx = 5, pady = 10, sticky="nesw", columnspan=4)
btnToggleDoor.grid(row = 4, column=0, padx = 5, pady = 10, columnspan = 2, sticky="nesw")
btnUpdateData.grid(row = 4, column=2, padx = 5, pady = 10, columnspan = 2, sticky="nesw")

# Setup the layout using grid
frmMain.grid()

# MQTT SETUP
mqttClient = mqtt.Client("ChickenCoopPC")
mqttClient.on_connect = mqttOnConnect
mqttClient.on_message = mqttOnMessage
mqttClient.message_callback_add("SmartChickenCoop/data/update", updateData)
mqttClient.connect("mqtt.eclipse.org", 1883)
mqttClient.loop_start()

# Get new data on startup
updateDataRequest()

# Window loop
window.mainloop()

# Close MQTT
mqttClient.loop_stop()
mqttClient.disconnect()
