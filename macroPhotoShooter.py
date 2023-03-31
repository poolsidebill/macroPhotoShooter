""" Shoot macro stacking photos with Canon R5 camera and 3d printer bed

    macroPhotoShooter.py
    bcase 04Feb2023

    Program controls connecting to both 3D-printer and camera. Printer connection
    is via serial interface and commands are via GCode and MCode. Camera
    connection and commanding is through Canon's CCAPI RESTful interface via
    WIFI connection.
    User is prompted for camera and subject information to determine the
    Depth of Field of the shots, bed movement for each shot, and estimated
    number of shots required and a time estimate of the entire shoot.
    Some number of shots will automatically be taken by looping through these
    commands: Move the bed, take picture. Each command blocks until finished
    to keep everythin sync'd.

    Note:
    1) Camera shutter setting should be set to single shot mode, otherwise the
       time between sending the shutter Press and Release commands allows
       multiple pictures to be taken instead  of only one.

"""
# import os
# import subprocess
import sys
import time
from datetime import datetime
from r5_cameraUtils import (
    createR5Session,
    depthOfField,
    stackingDOF,
    getLastEvent,
    shootR5Image,
    copyFiles,
    reportBatteryStatus,
)
from gcodeUtils import (
    connect3dPrinter,
    homePrinter,
    setAbsPositioning,
    setRelPositioning,
    quickMove,
    slowMove,
    setOrigin,
    gotoOrigin,
    printBedPosition,
    moveAxisZ,
)

# Globals
prtConn = None  # serial object used to communicate with printer
prtReady = False  # has connection to printer been established and bed configured
r5Session = None  # Request.Session object used to communicate with camera
camReady = (
    False
)  # camera has its CCAPI endpoint enabled and initial connection established
fStop = 0.0  # camera FStop for image capture
focalLen = 100  # focal length of camera lens - my default macro lens is 100mm
subjectDist = 0  # distance from subject to camera focal plane
subjectLen = 0  # length of subject capture
dof = 0.0  # calculated Depth of Field
bedMoveIncrement = 0.0  # calculated Y-axis movement between image captures
numShots = 0  # calculated number of shots required for subject capture
shotDirection = 1 # default direction is Front to Back. -1 for Back to Front

def setupPrinter(prtConn=None, homePrt=True, yAxis=110):
    """ Send 3D-printer to known location and move Z axis rail out of way

    Send printer to the known home of machine (this uses machine's limit switches).
    Move the bed to a known Y position that allows the bed to used as a platform
    for the macro subject. The Z rail holding the extruder is moved high out of
    the way. Configure 3D-printer to use relative positioning so bed movement
    commands only specify how far to move on each command, not to the actual
    XYZ axis position.

    Args:
      prtConn: serial port object connected to 3D-Printer
      homePrt: send the X,Y,Z axis to mechanical home position
      yAxis: starting Y position of bed
    """
    if homePrt:
        homePrinter(prtConn, True) # home X,Y but leave Z axis where it is
    setAbsPositioning(prtConn)
    # quickMove(prtConn, x=0, y=yAxis, z=190)  # adjust bed and move zrail out of way
    quickMove(prtConn, x=0, y=yAxis)  # adjust bed and move zrail out of way
    setRelPositioning(prtConn)  # 91
    setOrigin(prtConn)  # sets x=0 y=0 z=staysAtCurrentValue
    moveZ = input("\n\t Move Z axis out of way? y or (n): ")
    if not moveZ == "" or not  moveZ.upper() == 'N':
        moveAxisZ(prtConn)


def getShotParams():
    """ Inquire user about camera configuration and object placement

    Set the following based on user input. Prompt provided to fix mistakes before
    returning the values collected. All parameters are globals, and are used as the
    default values for each prompt.

    Globals updated:
      fStop - FStop setting of the camera
      focalLen - Focal length of lens (in mm)
      subjectDist - Distance leading edge of object is from the end of the camera lens
      subjectLen - Length of the subject photograph. Determines total bed movement
    """
    global fStop, focalLen, subjectDist, subjectLen
    while True:
        temp = input(f'\n\t Enter camera FStop (default={fStop}) : ')
        if not temp == "":
            fStop = float(temp)
        temp = input(f'\t Enter lens focal length (default={focalLen}) : ')
        if not temp == "":
            focalLen = int(temp)

        temp = input(f'\t Enter distance from lens to subject in mm (default={subjectDist}) : ')
        if not temp == "":
            subjectDist = int(temp)

        temp = input(f'\t Enter length of subject in mm (default={subjectLen}): ')
        if not temp == "":
            subjectLen = int(temp)

        paramTxt = "\n\t FStop= {fStop} Lens_length = {fLen}mm distance_to_object = {sDist}mm subject_size = {sLen}mm"
        print(
            paramTxt.format(
                fStop=fStop, fLen=focalLen, sDist=subjectDist, sLen=subjectLen
            )
        )
        response = input("\n\t Does this look right? y or n : ")

        if "Y" == response.upper():
            print("\n")
            break


def determineShotMovements(dof, objectLen):
    stackingDepth = stackingDOF(dof)
#    numShots = int(subjectLen / stackingDepth) + 4  # add extra. 2 before and 2 after
    numShots = int(subjectLen / stackingDepth) + 2  # add extra. 2 after
    return round(stackingDepth, 2), numShots


def decodeTime(seconds):
    sec = int(seconds)
    ty_res = time.gmtime(sec)
    return time.strftime("%H:%M:%S", ty_res)


def printShotEstimate(bedMoveIncrement, numShots):
    timeGuess = round(numShots * 1.1, 0)  #
    shotClockTxt = "\t Bed movement per shot = {bm}mm Number of shots = {ns}  estimated time (HH:MM:SS) = {et}"
    print("\n")
    print("++" * 50)
    print(
        shotClockTxt.format(bm=bedMoveIncrement, ns=numShots, et=decodeTime(timeGuess))
    )
    print("++" * 50)


def printMenu():
    menuStatusTxt = "\t Printer Connected: {prtStat} \t  Camera Connected: {camStat}\n"
    menuOptionTxt = "\t {optNum}  --- {opt}"
    print("\n\n\t\t Macro Photo Shooter Main Menu \n")
    print(menuStatusTxt.format(prtStat=prtReady, camStat=camReady))
    for key in menuOptionDict.keys():
        print(menuOptionTxt.format(optNum=key, opt=menuOptionDict[key]))



def checkPrinterStatus():
    try:
        # show if printer is connected and current X, Y,Z coordinates
        global prtConn, prtReady
        print("\tcheckPrinterStatus")
        if prtConn is None:
            resp = input("\tPrinter is not connected: Retry connection (y) or n: ")
            if resp == "" or "Y" == resp.upper():
                prtConn, success = connect3dPrinter()
                if success:
                    print("\t Printer connection established")
                    setupPrinter(prtConn)
                    prtReady = True
    except Exception as e:
        print("\n\t Exception detected: ", e)

    if not prtConn is None:
        # display printer status
        print("\tPrinter is connected: ", prtConn.is_open)
        printBedPosition(prtConn)
    else:
        print(
            "\t Printer is not connected. Ensure printer is on and cable is connected"
        )
        prtConn = None
        prtReady = False

    input("Press ENTER key to return to Main Menu ...")


def checkCameraStatus():
    global r5Session, camReady
    print("\tcheckCameraStatus")
    if r5Session is None:
        resp = input("\tCamera is not connected: Retry connection (y) or n: ")
        if resp == "" or "Y" == resp.upper():
            r5Session, camReady = createR5Session()

    if not r5Session is None:
        # display camera status
        try:
            reportBatteryStatus(r5Session)
            print("\nCamera is connected")

        except Exception as e:
            print("\n\t Exception detected: ", e)
            r5Session = None
            camReady = False
    else:
        print(
            "\t Camera is not connected. Ensure camera's CCAPI connection is set to Connect"
        )

    input("Press ENTER key to return to Main Menu ...")


def defineShotParameters():
    global dof, bedMoveIncrement, numShots

    print("\n\t --- Define Shot Parameters ---")
    while True:
        try:
            getShotParams()
            dof = depthOfField(dist=subjectDist, fStop=fStop, focalLen=focalLen)
            bedMoveIncrement, numShots = determineShotMovements(dof, subjectLen)

            # tell user about time info for these shots
            printShotEstimate( bedMoveIncrement, numShots )

            ready = input("\n\t Happy with Shot Parameters? (y) or n: ")
            if ready == "" or "Y" == ready.upper():
                print("\n")
                break
        except Exception as ex:
            print("-+" * 25)
            print("-+-+   Exception occurred: ",ex)
            print("-+-+   Please enter corrected shot parameters ")
            print("-+" * 25)


def checkShotEndpoints():
    global shotDirection, prtConn, bedMoveIncrement, numShots
    print("\n\t --- Check Shot Endpoints ---\n")
    print("\t Allows photographer to check the lighting and composition of the")
    print("\t subject at the begining and end of the shooting distances as")
    print("\t specified by the Define Shot Parameters menu option. \n")

    while True:
        if shotDirection > 0:
            print("\n\t Current shot direction is from Front to Back")
        else:
            print("\n\t Current shot direction is from Back to Front")

        tempStr = input("\t Is current shot direction correct? (y) or n: ")
        if tempStr == "" or "Y" == tempStr.upper():
            print("\n")
            break

        shotDirection *= -1 # change direction and prompt again to verify

    # cycle printer bed through endpoints until everyone is happy
    setRelPositioning(prtConn)  # 91
    positionLabel = ["Unkown", "Front", "Back"]
    directionTxt = "\t Current position: {}    "
    endptLocation = shotDirection
    while True:
        print(directionTxt.format(positionLabel[endptLocation]))
        printBedPosition( prtConn )
        tempStr = input("\tPress Enter to continue, or any key to exit endpoint checks and go back to home ")
        if not tempStr == "":
            # head back to shot's starting position
            slowMove(prtConn, y=0) # origin was already set during printer setup
            break

        # compute and head to next endpoint location
        ypos = round(bedMoveIncrement * numShots * endptLocation, 2)
        slowMove(prtConn, y=ypos)
        endptLocation *= -1


def performShotCaptures():
    global shotDirection, prtConn, r5Session,bedMoveIncrement, numShots
    print("\n\t --- Perform Shot Captures ---\n")
    if prtReady and camReady:
        # move printer to start positioning and clear camera polling buffer
         # start before subject
#        slowMove(prtConn, y=-round(bedMoveIncrement * 3 * shotDirection, 2))
        slowMove(prtConn, y=0)
        setRelPositioning(prtConn)  # 91
        result = getLastEvent(r5Session)  # clear polling buffer in camera

        startTime = datetime.now()
        for x in range(numShots):
            slowMove(prtConn, y=bedMoveIncrement * shotDirection)
            shootR5Image(session=r5Session, af=False)

        # final positon in Y-axis should be ~subject length
        printBedPosition( prtConn )
        stopTime = datetime.now()
        print("\n\t ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        print("\t    shot sequence completed. Elapsed time = ", (stopTime - startTime))
        paramTxt = "\n\tFStop= {fStop} Lens_length = {fLen}mm distance_to_object = {sDist}mm subject_size = {sLen}mm"
        print(paramTxt.format(fStop=fStop, fLen=focalLen, sDist=subjectDist, sLen=subjectLen))
        # tell user about time info for these shots
        printShotEstimate( bedMoveIncrement, numShots )

        # report image file names that were captured
        result = getLastEvent(r5Session)  # get all events from polling buffer
        addedList = result.get("addedcontents")  # only care about image(s) added
        print("\tImages captured:")
        for image in range(len(addedList)):
            print("\t\t", addedList[image])
        print("\t\t total image count = ", len(addedList))
        print("\n\t ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")

        # see if files should be copied
        cf = input("\n\t Copy files from camera to local directory?  (y) or n: ")
        if cf == "" or "Y" == cf.upper():
            copyFiles(r5Session, addedList)
        else:
            print(" \t...Files requested not to be copied locally")
    else:
        # Printer or Camera connectivity not established
        print("\n\t Error detected with connectivity as follows:")
        print("\t Printer connectivity established: ", prtReady)
        print("\t Camera connectivity established:  ", camReady)

    input("Press ENTER key to return to Main Menu ...")

def printBedLocation():
    # show if printer is connected and current X, Y,Z coordinates
    global prtConn
    print("\tPrint Bed Location")
    if prtConn is None:
        print("\tPrinter is not connected... ")
    else:
        # display printer status
        print("\tPrinter is connected: ", prtConn.is_open)
        printBedPosition(prtConn)

    input("Press ENTER key to return to Main Menu ...")

def changeZAxis():
    global prtConn
    moveAxisZ(prtConn)



# main
menuOptionDict = {
    1: "Printer Status",
    2: "Camera Status",
    3: "Define Shot Parameters",
    4: "Check Shot Endpoints",
    5: "Perform Shot Captures",
    6: "Print Bed Location",
    7: "Change Z-axis",
    8: "Exit",
}

try:
    print("\n Starting to connect to printer and camera...\n")

    while True:
        printMenu()
        selOption = ""
        try:
            selOption = int(input("Enter menu option: "))
        except:
            print("Wrong input choice selected. Please enter a valid number ...")

        if selOption == 1:
            checkPrinterStatus()
        elif selOption == 2:
            checkCameraStatus()
        elif selOption == 3:
            defineShotParameters()
        elif selOption == 4:
            checkShotEndpoints()
        elif selOption == 5:
            performShotCaptures()
        elif selOption == 6:
            printBedLocation()
        elif selOption == 7:
            changeZAxis()
        elif selOption == 8:
            print("\n\t Exiting program ...\n")
            sys.exit()
        else:
            print(
                "\n\tInvalid option selected. Enter number between 1 and ",
                len(menuOptionDict),
            )


except Exception as caughtEx:
    print("-+" * 20)
    print("Fatal exception detected")
    print(caughtEx)
    print("-+" * 20)
    print("\n")
