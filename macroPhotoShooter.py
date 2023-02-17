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
    1) Bed movement is TOWARDS the front of the machine, TOWARDS the camera.
       Camera should be pre-focused to front tip of subject.
    2) Camera shutter setting should be mechanical or 1st Electronic.
       Do NOT set shutter to Electronic.The time between sending the shutter
       Press and Release commands allows multiple pictures to be taken instead
       of only one.

"""
from r5_cameraUtils import *
from gcodeUtils import *

def setupPrinter(prtConn=None, homePrt=True, yAxis=120):
    """ Send 3D-printer to known location and move Z axis rail out of way

    Send printer to the known home of machine (this uses machine's limit switches).
    Move the bed to a known Y position that allows the bed to used as a platform
    for the macro subject. The Z rail holding teh extruder is moved high out of
    the way. Configure 3D-printer to use relative positioning so bed movement
    commands only specify how far to move on each command, not to the actual
    XYZ axis position.

    Args:
      prtConn: serial port object connected to 3D-Printer
      homePrt: send the X,Y,Z axis to mechanical home position
      yAxis: starting Y position of bed
    """
    if homePrt: homePrinter(prtConn)
    setAbsPositioning(prtConn)
    quickMove(prtConn, x=0, y=yAxis, z=190) # adjust bed and move zrail out of way
    setRelPositioning(prtConn) #91
    setOrigin(prtConn) # sets x=0 y=0 z=staysAtCurrentValue

def getShotParams():
    """ Inquire user about camera configuration and object placement

    Set the following based on user input. Prompt provided to fix mistakes before
    returning the values collected.

    Returns:
      fStop - FStop setting of the camera
      focalLen - Focal length of lens (in mm)
      subjectDist - Distance leading edge of object is from the end of the camera lens
      subjectLen - Length of the subject photograph. Determines total bed movement
    """
    while True:
        fStop = (float(input("\n\t Enter camera FStop: ")))
        focalLen = int((input("\t Enter lens focal length: ")))
        subjectDist = int((input("\t Enter distance from lens to subject (in mm): ")))
        subjectLen = int((input("\t Enter length of subject (in mm): ")))
        paramTxt = "\n\tFStop= {fStop} Lens_length = {fLen} distance_to_object = {sDist} subject_size = {sLen}"
        print(paramTxt.format(fStop=fStop, fLen=focalLen, sDist=subjectDist, sLen=subjectLen))
        response = input("\n\t Does this look right? y or n : ")

        if "Y" == response.upper():
            break

    return fStop, focalLen, subjectDist, subjectLen

def determineShotMovements( dof, objectLen):
    stackingDepth = stackingDOF(dof)
    numShots = int(subjectLen/stackingDepth) + 4 # add extra. 2 before and 2 after
    return round(stackingDepth,1), numShots

def decodeTime(seconds):
    sec = int(seconds)
    ty_res = time.gmtime(sec)
    return time.strftime("%H:%M:%S",ty_res)

def printShotEstimate(bedMoveIncrement, numShots):
    timeGuess = round(numShots * 1.1, 0) #
    shotClockTxt = "\t Bed movement per shot = {bm} Number of shots = {ns}  estimated time (HH:MM:SS) = {et}"
    print("\n")
    print("++" * 50)
    print( shotClockTxt.format(bm=bedMoveIncrement, ns=numShots, et=decodeTime(timeGuess)))
    print("++" * 50)


# main
print("\n Starting to connect to printer and camera...\n")
try:
    prtConn, success = connect3dPrinter()
    if success:
        setupPrinter(prtConn)
        prtReady = True

    r5Session, success = createR5Session()
    camReady = success

    while True:  # Setup for shooting until user has had enough

        if prtReady and camReady:
            # interfaces established
            fStop, focalLen, subjectDist, subjectLen = getShotParams()
            dof = depthOfField( dist=subjectDist, fStop=fStop,focalLen=focalLen)
            bedMoveIncrement, numShots = determineShotMovements( dof, subjectLen)
            printShotEstimate(bedMoveIncrement, numShots) # tell user about time info for these shots

            while True:
                ready = input("\n\t Ready for picture capture? y or n: ")
                if "Y" == ready.upper():
                    print("\n")
                    break
            # ready for the shots to begin
            # move printer to start positioning
            slowMove(prtConn, y= -round(bedMoveIncrement*3,1)) # start before subject
            startTime = datetime.now()
            for x in range(numShots):
                slowMove(prtConn, y=bedMoveIncrement)
                shootR5Image(session=r5Session, af=False)

            printBedPosition(prtConn) # final positon in Y-axis should be ~subject length
            stopTime = datetime.now()
            print("\n\t ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print("\t    shot sequence completed. Elapsed time = ", (stopTime-startTime))
            paramTxt = "\n\tFStop= {fStop} Lens_length = {fLen} distance_to_object = {sDist} subject_size = {sLen}"
            print(paramTxt.format(fStop=fStop, fLen=focalLen, sDist=subjectDist, sLen=subjectLen))
            printShotEstimate(bedMoveIncrement, numShots) # tell user about time info for these shots
            print("\n\t ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")

        else:
            print("-" * 45)
            print("\t Interface connection error detected:")
            print("\t\t 3D Printer ready: ",prtReady)
            print("\t\t R5 camera ready : ",camReady)
            print("-" * 45)
            break   # fatal error, exit the loop and exit
        # query if we want to setup for another shoot
        ready = input("\n\t Reset printer bed for another series of shots? y or n: ")
        if "N" == ready.upper():
            print("\n")
            break
        else:
            setAbsPositioning(prtConn)
            gotoOrigin(prtConn)
            setRelPositioning(prtConn)
            # go back to entering shot parameters


except Exception as e:
    print("-+" * 20)
    print("Fatal exception detected")
    print(e)
    print("-+" * 20)
    print("\n")
