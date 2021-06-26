#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Purpose: 
# Control Charging of your Car Battery to only use Power from your solar system
# 1) Read Kostal Inverter
# 2) Trigger shelly switch via MQTT based on Inverter Powergeneration and PowertoGrid
# 3) Shelly Switch is connected to a contactor that will be turned on/off to provide power to the car battery charger
# Version 1.0 
# Created June 20 2021
#
# Other Software components & Configuration required   
#   MQTT Server (I am using mosquitto on a Raspberry PI)
#   MQTT enabled on the Shelly Switch 
# Hardware required
#   Some machine to run this script (I am using a Raspberry PI)
#   Shelly Switch (I am using Shelly Switch 2.5
#   Contactor (since the Shelly switch I have (2.5) would overheat trying to switch a load higher than approx 500W)
#
# What you need to adapt in the code below line 40:
# IP adress of your broker (the MQTT server)
#    see broker= "192.168.178.39"
# Buffer  that needs to be reached to turn Shelly on/off
#   see self.MaxPowertoGridLimit = 500
# Threshold that needs to be met to start charging
#   see self.PanelThreshold = 3000 (W) - we only activate charging when we get more than 3000W Power generation from Panels
# Topic
# You need to check the MAC adress of your Shelly Switch and adapt the Topic you publish to
#   see TOPIC = "shellies/shellyswitch25-BCDDC277ABB0/relay/1/command"




import pymodbus
from pymodbus.client.sync import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.payload import BinaryPayloadBuilder
from pprint import pprint
import time
import collections
import argparse
import paho.mqtt.client as mqtt
import queue
import threading
import logging
from loggerdate import loggerdate


class wallbox (threading.Thread):
    def __init__ (self): 
        self.event = threading.Event()
        threading.Thread.__init__ (self)
        self.Lastwallboxstate = 0       #Init - Lastwallboxstate can be 0 (off - or 1- on)
        self.CapacityCounter = 0        # Buffer so we do not continuously switch box on / off 
        self.UpperThresholdCapacity = 3 # Threshold when we allow switching on/off of Wallbox
        self.LowerThresholdCapacity = -3
        self.MaxPowertoGridLimit = 500  # Buffer we leave remaining (W)
        self.PanelThreshold = 3000      # Threshold when we consider to charge WB
        self.Kostalquery = self.kostal_modbusquery()
    def switchwallbox (self,state):
        TOPIC = "shellies/shellyswitch25-BCDDC277ABB0/relay/1/command"
        ValueON = "on"
        ValueOff = "off"
        try:
            WBClient = mqtt.Client("WallboxServer")
            broker = "192.168.178.39"
            WBClient.connect(broker)
        except Exception as IssueMQTT:
            logging.error ("%s %s %s", loggerdate(),  ", Wallbox Error Subroutine switchwallbox issues init MQTT IssueMQTT is  , ", IssueMQTT)
            
        #print ("Mystate I got from master is", state)
        logging.info ("%s %s %s", loggerdate(),  ", Wallbox -INFO Subroutine switchwallbox wallbox to state , ", state)
        try:
            if state == 1:
                WBClient.publish(TOPIC, ValueON)
            else:
                #print ("Turning wallbox off")
                WBClient.publish(TOPIC, ValueOff) 
            WBClient.disconnect()
        except Exception as SWBError:
            logging.error ("%s %s %s", loggerdate(),  ", Wallbox -REALERROR Subroutine switchwallbox Error publishing to mqtt, ", SWBError)
 
    
        
    class kostal_modbusquery:
        def __init__(self):
            #Change the IP address and port to suite your environment:
            self.inverter_ip="192.168.178.41"
            self.inverter_port="1502"
            #No more changes required beyond this point
            self.KostalRegister = []
    
    
            self.Adr = collections.OrderedDict()
    
            self.Adr[6]   = [6,"Inverter article number", "Strg8"]
            self.Adr[46]  = [46,"Software-Version IO-Controller (IOC)", "Strg8"]
            self.Adr[56]  = [56,"Inverter State", "U16"]
            self.Adr[100] = [100,"Total DC power", "Float"]
    
            self.Adr[104] = [104,"State of energy manager","Float"]
            self.Adr[106] = [106,"Home own consumption from battery", "Float"]
    
            self.Adr[108] = [108,"Home own consumption from grid", "Float"]
            self.Adr[110] = [110,"Total home consumption Battery", "Float"]
    
            self.Adr[112] = [112,"Total home consumption Grid", "Float"]
            self.Adr[114] = [114,"Total home consumption PV", "Float"]
            self.Adr[116] = [116,"Home own consumption from PV", "Float"]
            self.Adr[118] = [118,"Total home consumption", "Float"]
            self.Adr[120] = [120,"Isolation resistance", "Float"]
            self.Adr[122] = [122,"Power limit from EVU", "Float"]
            self.Adr[124] = [124,"Total home consumption rate", "Float"]
            self.Adr[144] = [144,"Worktime", "Float"]
    
            self.Adr[150] = [150,"Actual cos phi", "Float"]
            self.Adr[152] = [152,"Grid frequency", "Float"]
            self.Adr[154] = [154,"Current Phase 1", "Float"]
            self.Adr[156] = [156,"Active power Phase 1", "Float"]
            self.Adr[158] = [158,"Voltage Phase 1", "Float"]
            self.Adr[160] = [160,"Current Phase 2", "Float"]
            self.Adr[162] = [162,"Active power Phase 2", "Float"]
            self.Adr[164] = [164,"Voltage Phase 2", "Float"]
            self.Adr[166] = [166,"Current Phase 3", "Float"]
    
            self.Adr[168] = [168,"Active power Phase 3", "Float"]
            self.Adr[170] = [170,"Voltage Phase 3", "Float"]
            self.Adr[172] = [172,"Total AC active power", "Float"]
            self.Adr[174] = [174,"Total AC reactive power", "Float"]
            self.Adr[178] = [178,"Total AC apparent power", "Float"]
            self.Adr[190] = [190,"Battery charge current", "Float"]
            self.Adr[194] = [194,"Number of battery cycles", "Float"]
            self.Adr[200] = [200,"Actual battery charge -minus or discharge -plus current", "Float"]
            self.Adr[202] = [202,"PSSB fuse state", "Float"]
            self.Adr[208] = [208,"Battery ready flag", "Float"]
            self.Adr[210] = [210,"Act. state of charge", "Float"]
            # self.Adr[212] = [212,"Battery state", "Float"]
            self.Adr[214] = [214,"Battery temperature", "Float"]
            self.Adr[216] = [216,"Battery voltage", "Float"]
            self.Adr[218] = [218,"Cos phi (powermeter)", "Float"]
            self.Adr[220] = [220,"Frequency (powermeter)", "Float"]
            self.Adr[222] = [222,"Current phase 1 (powermeter)", "Float"]
            self.Adr[224] = [224,"Active power phase 1 (powermeter)", "Float"]
            self.Adr[226] = [226,"Reactive power phase 1 (powermeter)", "Float"]
            self.Adr[228] = [228,"Apparent power phase 1 (powermeter)", "Float"]
            self.Adr[230] = [230,"Voltage phase 1 (powermeter)", "Float"]
            self.Adr[232] = [232,"Current phase 2 (powermeter)", "Float"]
            self.Adr[234] = [234,"Active power phase 2 (powermeter)", "Float"]
            self.Adr[236] = [236,"Reactive power phase 2 (powermeter)", "Float"]
            self.Adr[238] = [238,"Apparent power phase 2 (powermeter)", "Float"]
            self.Adr[240] = [240,"Voltage phase 2 (powermeter)", "Float"]
            self.Adr[242] = [242,"Current phase 3 (powermeter)", "Float"]
            self.Adr[244] = [244,"Active power phase 3 (powermeter)", "Float"]
            self.Adr[246] = [246,"Reactive power phase 3 (powermeter)", "Float"]
            self.Adr[248] = [248,"Apparent power phase 3 (powermeter)", "Float"]
            self.Adr[250] = [250,"Voltage phase 3 (powermeter)", "Float"]
            self.Adr[252] = [252,"Total active power (powermeter)", "Float"]
            self.Adr[254] = [254,"Total reactive power (powermeter)", "Float"]
            self.Adr[256] = [256,"Total apparent power (powermeter)", "Float"]
            self.Adr[258] = [258,"Current DC1", "Float"]
            self.Adr[260] = [260,"Power DC1", "Float"]
            self.Adr[266] = [266,"Voltage DC1", "Float"]
            self.Adr[268] = [268,"Current DC2", "Float"]
            self.Adr[270] = [270,"Power DC2", "Float"]
            self.Adr[276] = [276,"Voltage DC2", "Float"]
            self.Adr[278] = [278,"Current DC3", "Float"]
            self.Adr[280] = [280,"Power DC3", "Float"]
            self.Adr[286] = [286,"Voltage DC3", "Float"]
            self.Adr[320] = [320,"Total yield", "Float"]
            self.Adr[322] = [322,"Daily yield", "Float"]
            self.Adr[324] = [324,"Yearly yield", "Float"]
            self.Adr[326] = [326,"Monthly yield", "Float"]
            self.Adr[512] = [512,"Battery Gross Capacity", "U32"]
            self.Adr[514] = [514,"Battery actual SOC", "U16"]
            self.Adr[515] = [515,"Firmware Maincontroller (MC)", "U32"]
            self.Adr[517] = [517,"Battery Manufacturer", "Strg8"]
            self.Adr[525] = [525,"Battery Model ID", "U32"]
            self.Adr[527] = [527,"Battery Serial Number", "U32"]
            self.Adr[529] = [529,"Battery Operation mode", "U32"]
            self.Adr[531] = [531,"Inverter Max Power", "Float"]
            self.Adr[575] = [575,"Inverter Generation Power (actual)", "S16"]
            self.Adr[577] = [577,"Generation Energy", "U32"]
            # self.Adr[578] = [578,"Total energy", "U32"]
            self.Adr[580] = [580,"Battery Net Capacity", "U32"]
            self.Adr[582] = [582,"Actual battery charge-discharge power", "S16"]
            self.Adr[586] = [586,"Battery Firmware", "U32"]
            self.Adr[588] = [588,"Battery Type", "U16"]
            self.Adr[768] = [768,"Productname", "Strg32"]
            self.Adr[800] = [800,"Power Class", "Strg32"]
            self.Adr[1024] = [1024,"Battery charge power (AC) setpoint", "S16"]
            self.Adr[1025] = [1025,"Power Scale Factor", "S16"]
            self.Adr[1026] = [1026,"Battery charge power (AC) setpoint, absolute", "R32"]
            self.Adr[1028] = [1028,"Battery charge current (DC) setpoint, relative", "R32"]
            self.Adr[1030] = [1030,"Battery charge power (AC) setpoint, relative", "R32"]
            self.Adr[1032] = [1032,"Battery charge current (DC) setpoint, absolute", "R32"]
            self.Adr[1034] = [1034,"Battery charge power (DC) setpoint, absolute", "R32"]
            self.Adr[1036] = [1036,"Battery charge power (DC) setpoint, relative", "R32"]
            self.Adr[1038] = [1038,"Battery max charge power limit, absolute", "U32"]
            self.Adr[1040] = [1040,"Battery max discharge power limit, absolute", "U32"]
            self.Adr[1042] = [1042,"Minimum SOC", "U32"]
            self.Adr[1044] = [1044,"Maximum SOC", "U32"]
            self.Adr[1046] = [1046,"Total DC charge energy (DC-side to battery)", "R32"]
            self.Adr[1048] = [1048,"Total DC discharge energy (DC-side from battery)", "R32"]
            self.Adr[1050] = [1050,"Total AC charge energy (AC-side to battery)", "R32"]
            self.Adr[1052] = [1052,"Total AC discharge energy (Battery to grid)", "R32"]
            self.Adr[1054] = [1054,"Total AC charge energy (grid to battery)", "R32"]
            self.Adr[1056] = [1056,"Total DC PV energy (sum of all PV inputs)", "R32"]
            self.Adr[1058] = [1058,"Total DC energy from PV1", "R32"]
            self.Adr[1060] = [1060,"Total DC energy from PV2", "R32"]
            self.Adr[1062] = [1062,"Total DC energy from PV3", "R32"]
            self.Adr[1064] = [1064,"Total energy AC-side to grid", "R32"]
            self.Adr[1066] = [1066,"Total DC power (sum of all PV inputs)", "R32"]
            self.Adr[1068] = [1068,"Battery work capacity", "R32"]
            self.Adr[1070] = [1070,"Battery serial number", "U32"]
            self.Adr[1076] = [1076,"Maximum charge power limit (readout from battery)", "R32"]
            self.Adr[1078] = [1078,"Maximum discharge power limit (readout from battery)", "R32"]
            self.Adr[1080] = [1080,"Battery management mode", "U8"]
            self.Adr[1082] = [1082,"Installed sensor type", "U8"]
    
    
            self.Qty = dict()
            for key in self.Adr:
                self.Adr[key].append(None) # initial value
                self.Qty[self.Adr[key][1]] = self.Adr[key] # to search by name
    
    
    
    
        #-----------------------------------------
        # Routine to read a string from one address with 8 registers
        def ReadStr8(self,myadr_dec):
            r1=self.client.read_holding_registers(myadr_dec,8,unit=71)
            STRG8Register = BinaryPayloadDecoder.fromRegisters(r1.registers, byteorder=Endian.Big, wordorder=Endian.Little)
            result_STRG8Register =STRG8Register.decode_string(8)
            result_STRG8Register = bytes(filter(None,result_STRG8Register))    #Get rid of the "\X00"s
            return(result_STRG8Register)
        #-----------------------------------------
        # Routine to read a string from one address with 32 registers
        def ReadStr32(self,myadr_dec):
            r1=self.client.read_holding_registers(myadr_dec,32,unit=71)
            STRG32Register = BinaryPayloadDecoder.fromRegisters(r1.registers, byteorder=Endian.Big)
            result_STRG32Register =STRG32Register.decode_string(32)
            result_STRG32Register =bytes(filter(None,result_STRG32Register))    #Get rid of the "\X00"s
            return(result_STRG32Register)
        #-----------------------------------------
        # Routine to read a Float from one address with 2 registers
        def ReadFloat(self,myadr_dec):
            r1=self.client.read_holding_registers(myadr_dec,2,unit=71)
            FloatRegister = BinaryPayloadDecoder.fromRegisters(r1.registers, byteorder=Endian.Big, wordorder=Endian.Little)
            result_FloatRegister =round(FloatRegister.decode_32bit_float(),2)
            return(result_FloatRegister)
        #-----------------------------------------
        # Routine to read a U16 from one address with 1 register
        def ReadU16_1(self,myadr_dec):
            r1=self.client.read_holding_registers(myadr_dec,1,unit=71)
            U16register = BinaryPayloadDecoder.fromRegisters(r1.registers, byteorder=Endian.Big, wordorder=Endian.Little)
            result_U16register = U16register.decode_16bit_uint()
            return(result_U16register)
        #-----------------------------------------
        # Routine to read a U16 from one address with 2 registers
        def ReadU16_2(self,myadr_dec):
            r1=self.client.read_holding_registers(myadr_dec,2,unit=71)
            U16register = BinaryPayloadDecoder.fromRegisters(r1.registers, byteorder=Endian.Big, wordorder=Endian.Little)
            result_U16register = U16register.decode_16bit_uint()
            return(result_U16register)
        #-----------------------------------------
        # Routine to read a U32 from one address with 2 registers
        def ReadU32(self,myadr_dec):
            r1=self.client.read_holding_registers(myadr_dec,2,unit=71)
            #print ("r1 ", rl.registers)
            U32register = BinaryPayloadDecoder.fromRegisters(r1.registers, byteorder=Endian.Big, wordorder=Endian.Little)
            #print ("U32register is", U32register)
            #result_U32register = U32register.decode_32bit_float()
            result_U32register = U32register.decode_32bit_uint()
            return(result_U32register)
        #-----------------------------------------
        def ReadU32new(self,myadr_dec):
            #print ("I am in ReadU32new with", myadr_dec)
            r1=self.client.read_holding_registers(myadr_dec,2,unit=71)
            U32register = BinaryPayloadDecoder.fromRegisters(r1.registers, byteorder=Endian.Big, wordorder=Endian.Little)
            result_U32register = U32register.decode_32bit_uint()
            #result_U32register = U32register.decode_32bit_float()
            #print ("Here is what I got from ReadU32new", result_U32register)
            return(result_U32register)
        #-----------------------------------------
        # Routine to read a S16 from one address with 1 registers
        def ReadS16(self,myadr_dec):
            r1=self.client.read_holding_registers(myadr_dec,1,unit=71)
            S16register = BinaryPayloadDecoder.fromRegisters(r1.registers, byteorder=Endian.Big, wordorder=Endian.Little)
            result_S16register = S16register.decode_16bit_int()
            return(result_S16register)
        #-----------------------------------------
        # Routine to read a U8 from one address with 1 registers
        def ReadU8(self,myadr_dec):
            r1=self.client.read_holding_registers(myadr_dec,1,unit=71)
            U8register = BinaryPayloadDecoder.fromRegisters(r1.registers, byteorder=Endian.Big, wordorder=Endian.Little)
            #result_U8register = U8register.decode_8bit_uint()
            result_U8register = U8register.decode_16bit_uint()
            return(result_U8register)
    
        def WriteR32(self,myadr_dec,value):
    
            myreadregister= self.client.read_holding_registers(myadr_dec,2,unit=71)
            myreadregister = BinaryPayloadDecoder.fromRegisters(myreadregister.registers, byteorder=Endian.Big, wordorder=Endian.Little)
            myreadregister =round(myreadregister.decode_32bit_float(),2)
            print ("I read the value before setting it - value was ", myreadregister)
            mybuilder = BinaryPayloadBuilder(byteorder=Endian.Big,wordorder=Endian.Little)
            mybuilder.add_32bit_float(value)
            mypayload = mybuilder.build()
            mywriteregister=self.client.write_registers(myadr_dec,mypayload,skip_encode=True, unit=71)
            """
            print ("From  subroutine WriteS16 - In theory .... - I should get the value back that we pushed ", value ,"----", myreadregister)
            print("Register I wrote",mywriteregister)
            """
            return(mywriteregister)  
    
        def run(self):
    
            try:
                self.client = ModbusTcpClient(self.inverter_ip,
                                            port=self.inverter_port)
                self.client.connect()
    
                
                for key in self.Adr:                
                    dtype = self.Adr[key][2]
                    if dtype == "Strg8":
                        reader = self.ReadStr8
                    elif dtype == "U16":
                        reader = self.ReadU16_1
                    elif dtype == "Float":
                        reader = self.ReadFloat
                    elif dtype == "U8":
                        reader = self.ReadU8
                    elif dtype == "U32":
                        reader = self.ReadU32new
                    elif dtype == "S16":
                        reader = self.ReadS16
                    elif dtype == "Strg32":
                        reader = self.ReadStr32
                    elif dtype == "R32":
                        reader = self.ReadFloat
                    else:
                        print ("bad dtype", dtype)
                        raise ValueError("This Data type not known: %s"%dtype)
                        reader =self.ReadStr8 
    
                    val = reader(key)
                    self.Adr[key][3] = val
                    
    
    
                self.client.close()
    
                if self.Adr[575][3] > 32766: #Sometimes we hit the max value of 32767 - which implies a zero value
                    self.Adr[575][3] = 0
    
            except Exception as ex:
                logging.error ("%s %s %s", loggerdate(),  ", Wallbox Subroutine -Querykostal , ", ex)

    def run(self):  #Run command of class wallbox
        try:
            self.switchwallbox(0)           #Upon Initialization we turn the wallbox off 
            while not self.event.is_set():
                
                #Here is where we "do stuff"
                self.Kostalquery.run()
                
                self.PanelPowerGeneration= round(self.Kostalquery.Qty['Power DC1'][3] + self.Kostalquery.Qty['Power DC2'][3], 1)
                self.BatteryCharge = round( self.Kostalquery.Qty['Battery voltage'][3] *  self.Kostalquery.Qty['Actual battery charge -minus or discharge -plus current'][3], 1)
                self.TotalHomeconsumption =round((self.Kostalquery.Qty['Home own consumption from battery'][3]
                                + self.Kostalquery.Qty['Home own consumption from grid'][3]
                                + self.Kostalquery.Qty['Home own consumption from PV'][3]), 1)
                self.PowertoGrid = round(self.Kostalquery.Qty['Inverter Generation Power (actual)'][3] - self.TotalHomeconsumption,1)
                """
                print ("Panel Generation", self.PanelPowerGeneration)
                print ("PowertoGrid", self.PowertoGrid)
                print ("CapacityCounter",self.CapacityCounter)
                print ("Wallbox State", self.Lastwallboxstate)
                """

                # Logic Wallbox trigger
                
                
                if ((self.PanelPowerGeneration >self.PanelThreshold) and (not self.PowertoGrid >self.MaxPowertoGridLimit) and (self.Lastwallboxstate == 1)):
                    self.CapacityCounter = self.CapacityCounter -1
                    if (self.CapacityCounter <self.LowerThresholdCapacity):
                        logging.info ("%s %s %s", loggerdate(),  ", In Routine Wallbox INFO First If state clause , ", self.CapacityCounter)
                        self.Lastwallboxstate = 0
                        self.CapacityCounter = 0  
                        self.switchwallbox(0)
                if ((self.PanelPowerGeneration <self.PanelThreshold) and ( self.PowertoGrid <self.MaxPowertoGridLimit) and (self.Lastwallboxstate == 1)):
                    self.CapacityCounter = self.CapacityCounter -1
                    if (self.CapacityCounter <self.LowerThresholdCapacity):
                        logging.info ("%s %s %s", loggerdate(),  ", In Routine Wallbox INFO Second If state clause , ", self.CapacityCounter)
                        self.Lastwallboxstate = 0
                        self.CapacityCounter = 0  
                        self.switchwallbox(0)
                if ((self.PanelPowerGeneration >self.PanelThreshold) and ( self.PowertoGrid >self.MaxPowertoGridLimit) and (self.Lastwallboxstate == 0)):
                    self.CapacityCounter = self.CapacityCounter +1
                    if (self.CapacityCounter >self.UpperThresholdCapacity):
                        logging.info ("%s %s %s", loggerdate(),  ", In Routine Wallbox INFO Third If state clause , ", self.CapacityCounter)
                        self.Lastwallboxstate = 1
                        self.CapacityCounter = 0  
                        self.switchwallbox(1)                        
                                
                time.sleep(5)
                
                
                
        except Exception as ShitHitFan:
            #print ("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
            logging.error ("%s %s %s", loggerdate(),  ", Ran into Error in  Routine Wallbox , ", ShitHitFan)
    
    
if __name__ == "__main__":
    try:
        debugfile = "./wbloggingoutput.log"                             #File we write to from the logging module
        logging.basicConfig(filename=debugfile,level=logging.ERROR)
        logging.basicConfig(format='%(asctime)s.%(msecs)d %(levelname)s %(module)s - %(funcName)s: %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
        print ("Purpose: Start thread that does the heavy lifting to query Kostal - and trigger the Shelly Switch")
        MyWallboxThread = wallbox()
        print ("Wallbox -Main - starting")
        MyWallboxThread.start()
        print ("Wallbox Main - started")
    except Exception as BAD:
        print ("Bad was ...", BAD)
               
    except KeyboardInterrupt:
        #In case the user hits Ctrl-C 
        print ("Program killed by user... \n") 
        logging.error ("%s %s", loggerdate(),  ", User hit Ctrl-C, ")
        MyWallboxThread.event.set()


