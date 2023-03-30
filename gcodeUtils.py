""" gcodeTest.py
   bcase 31Jan2023
   Setup/test control of 3D Printer via USB serial interface.
   GCodes are buffered so you must insert M400 MCode to force controller to
   complete current command in buffer before accepting next command.
"""
import serial
import time, math

def sendGCodeCmd(ser, command):
    cmdResponse = ""
    print("\t Sending GCode command: ", command.strip("\r\n"))
    ser.write(str.encode(command))  # serial write is a blocking command
    time.sleep(0.4)

    while True:
        line = ser.readline()
        print("\t cmd resp: ", line)
        if not line == b"ok\n":
            cmdResponse = line
        elif line == b"ok\n":
            # there is room in buffer for another command
            break

    return cmdResponse


def connect3dPrinter():
    serialConn = serial.Serial("/dev/ttyUSB0", 256000)  # Mega I3 Marlin FW v1.1.9
    time.sleep(5)  # let printer board do its thing
    print("\t serial port is open: ", serialConn.is_open)
    # return serialConn, serialConn.isOpen()
    return serialConn, serialConn.is_open


def beep3dPrinter(serConn):
    sendGCodeCmd(serConn, "M300 S440 P200\r\n")  # print completed sound - Marlin FW


def homePrinter(serConn, ignoreZ=True):
    """ Send X-axis and Y-axis to their stops

    Default only moves X and Y axises and ignores Z position since this utility
    is primarily used to control the printer bed.
    """
    if ignoreZ is True:
        sendGCodeCmd(serConn, "G28 X Y\r\n")  # Home only X and Y
    else:
        sendGCodeCmd(serConn, "G28\r\n")  # Home all axises

    sendGCodeCmd(serConn, "M400\r\n")  # wait for buffered command to finish


def quickMove(serConn, x=math.nan, y=math.nan, z=math.nan):
    cmd = "G0 "
    if not math.isnan(x):
        cmd = "%s X%s " % (cmd, x)
    if not math.isnan(y):
        cmd = "%s Y%s " % (cmd, y)
    if not math.isnan(z):
        cmd = "%s Z%s " % (cmd, z)
    sendGCodeCmd(serConn, cmd + "\r\n")  #
    sendGCodeCmd(serConn, "M400\r\n")  # wait for buffered command to finish


def slowMove(serConn, x=math.nan, y=math.nan, z=math.nan, feedRate=120):
    cmd = "G0 "
    if not math.isnan(x):
        cmd = "%s X%s " % (cmd, x)
    if not math.isnan(y):
        cmd = "%s Y%s " % (cmd, y)
    if not math.isnan(z):
        cmd = "%s Z%s " % (cmd, z)
    cmd = "%s F%s\r\n" % (cmd, feedRate)
    sendGCodeCmd(serConn, cmd)  #
    sendGCodeCmd(serConn, "M400\r\n")  # wait for buffered command to finish


def getBedPositon(serConn):
    # example of returned bytes object from printer
    # "b'X:1.00 Y:10.01 Z:175.00 E:0.00 Count X:3200 Y:6000 Z:70000\n'"
    axis = sendGCodeCmd(serConn, "M114\r\n")  # report all axises
    axisStr = axis.decode()  # convert bytes to string
    cutString = axisStr.split(":")
    x = float(cutString[1][:-2])
    y = float(cutString[2][:-2])
    z = float(cutString[3][:-2])
    return x, y, z


def printBedPosition(serConn):
    x, y, z = getBedPositon(serConn)
    bedPosTxt = "\tBed Position: x={x} y={y} z={z}"
    print(bedPosTxt.format(x=x, y=y, z=z))


def setAbsPositioning(serConn):
    sendGCodeCmd(serConn, "G90\r\n")  # absolute positioning


def setRelPositioning(serConn):
    sendGCodeCmd(serConn, "G91\r\n")  # relative positioning


def setInchUnits(serConn):
    sendGCodeCmd(serConn, "G20\r\n")  # set machine to use inches


def setMmUnits(serConn):
    sendGCodeCmd(serConn, "G21\r\n")  # set machine to use millimeters


def setPosition(serConn, x=math.nan, y=math.nan, z=math.nan):
    cmd = "G92 "
    if not math.isnan(x):
        cmd = "%s X%s " % (cmd, x)
    if not math.isnan(y):
        cmd = "%s Y%s " % (cmd, y)
    if not math.isnan(z):
        cmd = "%s Z%s " % (cmd, z)
    sendGCodeCmd(serConn, cmd + "\r\n")  #


def savePosition(serConn, slotNum=0):  # not suppported by my 3dPrinter
    cmd = "G60 S" + str(slotNum)
    sendGCodeCmd(serConn, cmd + "\r\n")


def gotoSavedPos(serConn, slotNum=0):  # not suppported by my 3dPrinter
    cmd = "G61 F120 XYZ S" + str(slotNum)
    sendGCodeCmd(serConn, cmd + "\r\n")


def setOrigin(serConn):
    setPosition(serConn, x=0, y=0)  # force new xy positoins, Z remains the same
    # savePosition(serConn, slotNum=0 ) # save origin in slot #0


def gotoOrigin(serConn):
    slowMove(serConn, x=0, y=0, feedRate=120)

def moveAxisZ(serConn):
    dirVal = ['Unknown', 'UP','DOWN']

    print("\n\t Move the Z axis. Specify the following:")
    print("\t\t Direction: Up = '+'  Down = '-'")
    print("\t\t Distance in mm")
    print("\t\t    example: UP 170mm -> +170 or DOWN 23.4mm -> -23.4")
    while True:
        moveInput = input("\n\t Enter direction and distance:  ")
        if not moveInput == "":
            if moveInput[0] == '-' :
                direction = -1  # DOWN
            elif moveInput[0] == '+':
                direction = 1 # UP
            else:
                direction = 0  # Unknown

            try:
                dist = float(moveInput[1:])
                print("\t requested movement: {} {}mm".format(dirVal[direction], dist))
                if not direction == 0:
                    setRelPositioning(serConn)
                    slowMove(serConn, z=(dist*direction))
                    break
                else:
                    print("\t Invalid entry for direction. Specify '+' or '-'")

            except Exception as ex:
                print("\n\t Exception: Invalid entry for distance. \n",ex)
        else:
            print("\t Invalid entry")


# Main
def main():

    ser, result = connect3dPrinter()
    print("printer connected: ", result)

    homePrinter(ser, False) # home all three axises
    x, y, z = getBedPositon(ser)
    bedPosTxt = "Bed Position: x={x} y={y} z={z}"
    print(bedPosTxt.format(x=x, y=y, z=z))  # s/b  x=-5.0 y=0.0 z=0.0

    quickMove(ser, x=10, y=20, z=40)
    x, y, z = getBedPositon(ser)
    print(bedPosTxt.format(x=x, y=y, z=z))  # s/b x=10.0 y=20.0 z=40.0

    setRelPositioning(ser)  # 91
    slowMove(ser, y=10, feedRate=60)
    x, y, z = getBedPositon(ser)
    print(bedPosTxt.format(x=x, y=y, z=z))  # s/b x=10.0 y=20.0 z=40.0

    setOrigin(ser)  # sets x=0 y=0 z=staysAtCurrentValue
    x, y, z = getBedPositon(ser)
    print(bedPosTxt.format(x=x, y=y, z=z))  # s/b x=0.0 y=0.0 z=40.0

    slowMove(ser, y=10, feedRate=60)
    x, y, z = getBedPositon(ser)
    print(bedPosTxt.format(x=x, y=y, z=z))  # s/b x=0.0 y=10.0 z=40.0

    moveAxisZ(ser)

    time.sleep(1)
    ser.close()


if __name__ == "__main__":
    main()

"""
Start Code - Cura
 G21                                        ; metric values
 G90                                        ; absolute positioning
 M82                                        ; set extruder to absolute mode
 M107                                       ; start with the fan off
 M190 S{material_bed_temperature_layer_0}   ; preheat and wait for bed
 M109 S{material_print_temperature_layer_0} ; preheat and wait for hotend
 M300 S1000 P500                            ; BEEP heating done
 G28 X0 Y10 Z0                              ; move X/Y to min endstops
 M420 S1                                    ; enable mesh leveling
 G0 Z0.15                                   ; lift nozzle a bit
 G0 X2                                      ; move away from clips
 G92 E0                                     ; zero the extruded length
 G1 Y50 E25 F500                            ; Extrude 25mm of filament in a 5cm line.
 G92 E0                                     ; zero the extruded length again
 G1 E-2 F500                                ; Retract a little
 G1 Y120 F4000                              ; Quickly wipe away from the filament line

End Code - Cura
 M104 S0                                    ; Extruder off
 M140 S0                                    ; Heatbed off
 M107                                       ; Fan off
 G91                                        ; relative positioning
 G1 E-5 F300                                ; retract a little
 G1 Z+10                                    ; lift print head
 G28 X0 Y0                                  ; homing
 G1 Y180 F2000                              ; reset feedrate
 M84                                        ; disable stepper motors
 G90                                        ; absolute positioning
 M300 S440 P200                             ; Make Print Completed Tones
 M300 S660 P250                             ; beep
 M300 S880 P300                             ; beep
"""
