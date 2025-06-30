print("##########################################################################################")
print(">>>>> SM - Running version __1__ of TemperatureSensorIntegration.py <<<<<")
#VERSION = "SM - TemperatureSensorIntegration.py - __1__ Copy - June 2025"
# raspberry pi path, not the local computer path:
#EXPECTED_PATH = "/home/shaynamitchell/cs350/Module-6/TemperatureSensorIntegration.py"
#
print("#####                             Shayna Mitchell                           #####")
print("##                                  June 2025                                  ##")
print("##                           CS350 Embedded Systems                            ##")
print("##           Module Six Lab Adding a Temperature and Humidity System           ##")
print("##        VERSION: 1 - no edits were necessary as was already complete.        ##")
print("#####                                                                       #####")
#
#####    Could add a check here to make sure you aren't running the wrong file again:
#import os, sys
#if __file__ != EXPECTED_PATH:
#    print("\n WARNING: You are NOT running the correct file!")
#    print(f"Expected path: {EXPECTED_PATH}")
#    print(f"Running from: {__file__}")
#    print("Tip: Copy the correct file to the Pi and run from ~/cs350/Module-6")
#    sys.exit(1)
#else:
#    print(f"Running expected file: {__file__}")
#    print(f"VERSION: {VERSION}")
#
#####    Running instructions via terminal:    #####
##copy new edits to:
# scp ~/Documents/ShaynaWorkspace/School/CS-350/Module-6/TemperatureSensorIntegration.py shaynamitchell@192.168.12.179:~/cs350/Module-6/
## and run like this:
# cd cs350
# ls
# cd Module-6
#ls
# sudo python3 TemperatureSensorIntegration.py
#
######
# TemperatureSensorIntegration.py - This is the Python code template 
# used to demonstrate the integration of the temperature sensor with
# some of our other components. 
#
# The goal of this module will be to display the temperature on our 
# 16x2 display, and when the button is pressed switch between 
# displaying the temperature in Celsius or Fahrenheit. 
#
# We will manage transitions between temperature scales with a state
# machine.
#
# This code works with the test circuit that was built for module 6.
#
#------------------------------------------------------------------
# Change History
#------------------------------------------------------------------
# Version   |   Description
#------------------------------------------------------------------
#    1          Initial Development
#------------------------------------------------------------------
#####
##
## Imports required to handle our Button, and our LED devices
##
from gpiozero import Button, LED

##
## Imports required to allow us to build a fully functional state machine
##
from statemachine import StateMachine, State

##
## Import required to allow us to pause for a specified length of time
##
from time import sleep
from datetime import datetime

##
## These are the packages that we need to pull in so that we can work
## with the GPIO interface on the Raspberry Pi board and work with
## the 16x2 LCD display
##
import board
import digitalio
import adafruit_character_lcd.character_lcd as characterlcd

##
## This is the package we need for our Temperature Sensor
##
import adafruit_ahtx0

##
## Threads are required so that we can manage multiple tasks
## at the same time
##
from threading import Thread

##
## DEBUG flag - boolean value to indicate whether or not to print 
## status messages on the console of the program
## 
DEBUG = True

##
## ManagedDisplay - Class intended to manage the 16x2 
## Display
##
## This code is largely taken from the work done in module 4, and
## converted into a class so that we can more easily consume the 
## operational capabilities.
##
class ManagedDisplay():
    ##
    ## Class Initialization method to setup the display
    ##
    def __init__(self):
        ##
        ## Setup the six GPIO lines to communicate with the display.
        ## This leverages the digitalio class to handle digital 
        ## outputs on the GPIO lines. There is also an analagous
        ## class for analog IO.
        ##
        ## You need to make sure that the port mappings match the
        ## physical wiring of the display interface to the 
        ## GPIO interface.
        ##
        ## compatible with all versions of RPI as of Jan. 2019
        ##
        self.lcd_rs = digitalio.DigitalInOut(board.D17)
        self.lcd_en = digitalio.DigitalInOut(board.D27)
        self.lcd_d4 = digitalio.DigitalInOut(board.D5)
        self.lcd_d5 = digitalio.DigitalInOut(board.D6)
        self.lcd_d6 = digitalio.DigitalInOut(board.D13)
        self.lcd_d7 = digitalio.DigitalInOut(board.D26)

        # Modify this if you have a different sized character LCD
        self.lcd_columns = 16
        self.lcd_rows = 2 

        # Initialise the lcd class
        self.lcd = characterlcd.Character_LCD_Mono(self.lcd_rs, self.lcd_en, 
                    self.lcd_d4, self.lcd_d5, self.lcd_d6, self.lcd_d7, 
                    self.lcd_columns, self.lcd_rows)

        # wipe LCD screen before we start
        self.lcd.clear()

    ##
    ## cleanupDisplay - Method used to cleanup the digitalIO lines that
    ## are used to run the display.
    ##
    def cleanupDisplay(self):
        # Clear the LCD first - otherwise we won't be abe to update it.
        self.lcd.clear()
        self.lcd_rs.deinit()
        self.lcd_en.deinit()
        self.lcd_d4.deinit()
        self.lcd_d5.deinit()
        self.lcd_d6.deinit()
        self.lcd_d7.deinit()
        
    ##
    ## clear - Convenience method used to clear the display
    ##
    def clear(self):
        self.lcd.clear()

    ##
    ## updateScreen - Convenience method used to update the message.
    ##
    def updateScreen(self, message):
        self.lcd.clear()
        self.lcd.message = message

    ## End class ManagedDisplay definition  
    

##
## TempMachine - This is our StateMachine implementation class.
## The purpose of this state machine is to maintain the necessary
## state to display temperature information in Celsius or Fahrenheit
##
class TempMachine(StateMachine):
    "A state machine designed to manage temperature messages"

    ## Our two LEDs, utilizing GPIO 18, and GPIO 23
    ##
    redLight = LED(18)
    blueLight = LED(23)

    ##
    ## Set the contents of our scale
    ##
    scale1 = 'F'
    scale2 = 'C'

    ##
    ## keep track of the active scale
    ##
    activeScale = scale2

    ##
    ## Define these states for our machine.
    ##
    ##  Celsius - default
    ##  Fahrenheit
    ##
    Celsius = State(initial = True)
    Fahrenheit = State()

    ##
    ## Configure our display
    ##
    screen = ManagedDisplay()

    ##
    ## Configure our temperature sensor
    ##
    i2c = board.I2C()
    thSensor = adafruit_ahtx0.AHTx0(i2c)

    ##
    ## doDot - Event that moves between the off-state (all-lights-off)
    ## and a 'dot'
    ##
    cycle = (
        Celsius.to(Fahrenheit) | Fahrenheit.to(Celsius)
    )

    ##
    ## on_enter_Celsius - Action performed when the state machine transitions
    ## into the Celsius state
    ##
    def on_enter_Celsius(self):
        # Change scale
        self.activeScale = self.scale2
        if(DEBUG):
            print("* Changing state to Celsius")

    ##
    ## on_enter_Fahrenheit - Action performed when the state machine transitions
    ## into the Celsius state
    ##
    def on_enter_Fahrenheit(self):
        # Change scale
        self.activeScale = self.scale1
        if(DEBUG):
            print("* Changing state to Fahrenheit")

    ##
    ## processButton - Utility method used to send events to the 
    ## state machine. This event triggers a change in state to 
    ## swap between Fahrenheit and Celsius output
    ##
    def processButton(self):
        print('*** processButton')
        self.send("cycle")

    ##
    ## run - kickoff the display management functionality in a
    ## separate execution thread.
    ##
    def run(self):
        myThread = Thread(target=self.displayTemp)
        myThread.start()

    ##
    ## Get the temperature in Fahrenheit
    ##
    def getFahrenheit(self):
        t = self.thSensor.temperature
        return (((9/5) * t) + 32)

    ##
    ## Get the temperature in Celsius
    ##
    def getCelsius(self):
        return self.thSensor.temperature

    ##
    ## Get the Relative Humidity
    ##
    def getRH(self):
        return self.thSensor.relative_humidity

    ##
    ## Flag to indicate whether or not to shutdown the thread
    ##
    endDisplay = False

    ##
    ## displayTemp - utility method used to continuously update
    ## the display. We will be putting the date and time in row 1,
    ## and the Temperature and Relative Humidity in Row 2.
    ##
    def displayTemp(self):

        ##
        ## Loop until we are shutdown
        ##
        while not self.endDisplay:

            ## Setup line 1
            line1 = datetime.now().strftime('%b %d  %H:%M:%S\n')

            ## Setup line 2
            if self.activeScale == 'C':
                line2 = f"T:{self.getCelsius():0.1f}C H:{self.getRH():0.1f}%"
            else:
                line2 = f"T:{self.getFahrenheit():0.1f}F H:{self.getRH():0.1f}%"

            self.screen.updateScreen(line1 + line2)
            sleep(1)

        ## Cleanup the display i.e. clear it
        self.screen.cleanupDisplay()



    ## End class CWMachine definition


##
## Initialize our State Machine, and begin transmission
##
tempMachine = TempMachine()
tempMachine.run()

##
## greenButton - setup our Button, tied to GPIO 24. Configure the
## action to be taken when the button is pressed to be the 
## execution of the processButton function in our State Machine
##
greenButton = Button(24)
greenButton.when_pressed = tempMachine.processButton

##
## Setup loop variable
##
repeat = True

##
## Repeat until the user creates a keyboard interrupt (CTRL-C)
##
while repeat:
    try:
        ## Only display if the DEBUG flag is set
        if(DEBUG):
            print("Killing time in a loop...")

        ## sleep for 20 seconds at a time. This value is not crucial, 
        ## all of the work for this application is handled by the 
        ## Button.when_pressed event process
        sleep(20)
    except KeyboardInterrupt:
        ## Catch the keyboard interrupt (CTRL-C) and exit cleanly
        ## we do not need to manually clean up the GPIO pins, the 
        ## gpiozero library handles that process.
        print("END OF WEEK SIX TEMPERATURE SENSOR CODE PROJECT FILE CS350 Emerging Systems SM June 2025. Cleaning up. Exiting...")

        ## Stop the loop
        repeat = False
        
        ## Cleanly exit the state machine after completing the last message
        tempMachine.endDisplay = True
        sleep(1)
#
# END OF WEEK SIX TEMPERATURE SENSOR CODE PROJECT FILE CS350 Emerging Systems SM June 2025
##########################################################################################