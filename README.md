# LowCostSmartWallbox
Purpose
Control Charging of your Car Battery to only use Power from your solar system
1) Read Kostal Inverter via ModBus TCP
2) Trigger Shelly Switch via MQTT based on Inverter Powergeneration and PowertoGrid
3) Shelly Switch is connected to a contactor that will be turned on/off to provide power to the car battery charger