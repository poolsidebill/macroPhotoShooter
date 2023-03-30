""" r5_cameraUtils.py
    bcase 02Feb2023
    Helpful Canon R5 functions
"""
import sys
import traceback
import time
import math
import os
import requests
from requests.exceptions import Timeout

# Constants
API_URL = "http://192.168.1.188:8080"  # my harcoded network endpoint for camera

R5_COC = 0.00439  # pixelsize of R5 sensor


def createR5Session(apiUrl=API_URL):
    """ A single session for all requests keeps multiple connection requests
      from being refused by the camera
      Supressing full traceback, will print top-level exception
    """
    success = False
    try:
        sys.tracebacklimit = 10  # only the exception type and value are printed
        session = requests.Session()
        print(
            "initial CCAPI session response: ",
            session.get(apiUrl + "/ccapi", timeout=(2, 5)),
        )  # establish inital connection
        success = True
    except Exception as e:
        session.close()
        session = None 
        print("Exception detected in createR5Session")
        print(e)
        # print("-"*60)
        # traceback.print_exc(file=sys.stdout)
        # print("-"*60)

    return session, success


def sendR5CcapiCmd(session, resource, cmdData, apiURL=API_URL):
    """ Command camera resource via a POST request

    Inputs:
       session - Session object currently connected to camera
       resource - CCAPI resource path
       cmdData - dictionary of parameter:value data items to update
       apiURL - domain and port URL

    Returns:
       resp - response payload from CCAPI
    """
    resp = {}
    try:
        resp = session.post(apiURL + resource, json=cmdData, timeout=(2, 5))
        # print(resp)
    except requests.exceptions.Timeout as errt:
        print("\t Timeout happened on request", errt)
    except requests.exceptions.ConnectionError as errc:
        print("\t", errc)

    return resp


def sendR5CcapiReq(session, resource, apiURL=API_URL):
    """ Request data from camera via a GET request

    Inputs:
       session - Session object currently connected to camera
       resource - CCAPI resource path
       apiURL - domain and port URL

    Returns:
       resp - response payload from CCAPI
    """
    resp = {}
    try:
        resp = session.get(apiURL + resource, timeout=(2, 5))
        # print(resp)
    except requests.exceptions.Timeout as errt:
        print("\t Timeout happened on request", errt)
    except requests.exceptions.ConnectionError as errc:
        print("\t", errc)

    return resp


def sendR5CcapiDelete(session, resource, apiURL=API_URL):
    """ Remove data from camera via a DELETE request

    Inputs:
       session - Session object currently connected to camera
       resource - CCAPI resource path to delete
       apiURL - domain and port URL

    Returns:
       resp - response payload from CCAPI
    """
    resp = {}
    try:
        resp = session.delete(apiURL + resource, timeout=(2, 5))
        # print(resp.status_code)
    except requests.exceptions.Timeout as errt:
        print("\t Timeout happened on request", errt)
    except requests.exceptions.ConnectionError as errc:
        print("\t", errc)

    return resp


def decodeR5CcapiResponse(resp):
    respDict = resp.json()
    #    print("CCAPI response items: ", respDict.items()) # all key:value pairs
    print("decodeR5CcapiResponse: ", respDict.get("message"))


def getCurrentDir(session, apiURL=API_URL):
    """ Determine the current folder for image captures

    Returns:
      name - folder name (i.e. 111STRB3). If "", the media is not mounted in the camera
      path - full path including name (i.e.  /ccapi/ver130/contents/sd/111STRB3).
             If "", the media is not mounted in the camera
    """
    curDirReq = "/ccapi/ver110/devicestatus/currentdirectory"
    response = sendR5CcapiReq(session, curDirReq, apiURL)
    respDict = response.json()
    return respDict.get("name"), respDict.get("path")

def reportBatteryStatus(session, apiURL=API_URL):
    """ Determine the current folder for image captures

    Returns:
      name - folder name (i.e. 111STRB3). If "", the media is not mounted in the camera
      path - full path including name (i.e.  /ccapi/ver130/contents/sd/111STRB3).
             If "", the media is not mounted in the camera
    """
    curDirReq = "/ccapi/ver100/devicestatus/battery"
    response = sendR5CcapiReq(session, curDirReq, apiURL)
    respDict = response.json()
    print("\t\t Camera Battery Status")
    for key,val in respDict.items():
        print("\t name: {} \t value: {}".format(key, val))



def getNumDirEntries(session, path, apiURL=API_URL):
    """ Get the number of entries in a folder and the number of pages required to get all the images

    Inputs:
       session - Session object currently connected to camera
       path - CCAPI resource path of folder
       apiURL - domain and port URL

     Returns:
       number - total number of images in requested folder
       pageCount - number of "chunked" pages needed to all entries. CCAPI can only
           return 100 entries at a time, so they split it up into 100 entry chunks
    """
    params = "?kind=number"
    response = sendR5CcapiReq(session, path + params, apiURL)
    respDict = response.json()
    return respDict.get("contentsnumber"), respDict.get("pagenumber")


def getLastEvent(session, apiURL=API_URL):
    """ Retrieve the camera's polling buffer
    """
    pollingReqPath = "/ccapi/ver100/event/polling"
    response = sendR5CcapiReq(session, pollingReqPath, apiURL)
    print("getLastEvent: status code = ", response.status_code)
    respDict = response.json()
    return respDict


def shootR5Image(session, apiURL=API_URL, af=True):
    """ Capture a single picture image on the R5
    Handles rety if the camera is busy (i.e. storing a previous picture)
    """
    CTRL_BTN = "/ccapi/ver100/shooting/control/shutterbutton/manual"
    PRESS_PRAM = {"action": "full_press", "af": True}
    RELEASE_PRAM = {"action": "release", "af": True}

    success = False
    paramDict = PRESS_PRAM
    if not af:
        paramDict["af"] = False

    while True:
        result = sendR5CcapiCmd(
            session, resource=CTRL_BTN, cmdData=PRESS_PRAM
        )  # press shutter button
        # print("cmd sent. result:",result.status_code)
        print("cmd sent. result:", result)
        time.sleep(0.15)
        if result == {}:
            return success  # serious error
        if not result.status_code == 503:  # retry loop if camera is busy
            break

    # command was accepted, check its status
    if result and result.status_code == 200:
        result = sendR5CcapiCmd(
            session, resource=CTRL_BTN, cmdData=RELEASE_PRAM
        )  # release shutter button
        if result and result.status_code == 200:
            # Success
            print("Camera image captured")
            time.sleep(0.4)  # give some time to store image
            success = True
        else:
            print("Camera command to release shutter button failed")
            decodeR5CcapiResponse(result)
    else:
        print("Camera command to press shutter button failed.", result)
        decodeR5CcapiResponse(result)

    return success


def getImage(session, imagePath, apiURL=API_URL):
    """ Get an image from camera folder

    Retrieve an image and reports an error message if it was not able to
    fetch it. Fetches the JPEG version of image

    Inputs:
       session - Session object currently connected to camera
       imagePath - CCAPI resource path of image to be fetched
                 (i.e. /ccapi/ver130/contents/sd/111STRB3/IMG_7935.JPG )
       apiURL - domain and port URL

     Returns:
       resp - response payload from CCAPI
    """
    params = "?kind=display"  # fetch the JPEG version
    response = sendR5CcapiReq(session, imagePath, apiURL)
    # print(" headers = ", response.headers)
    # print(" Content-Type = ", response.headers.get("Content-Type"))
    return response


def copyFiles(session, addedList):
    """ Retrieve camera images and store them locally

    Query user for a directory name to copy files into. Create the directory
    if needed. If no directory is specified, use current directory as the destination.
    Cycle through input list of resource images, fetch and save file locally. Names of
    files are listed after copied.

    Inputs:
       session - Session object currently connected to camera
       addedList - List of CCAPI resource path(s) of image(s) to be fetched
                 (i.e. /ccapi/ver130/contents/sd/111STRB3/IMG_7935.JPG )

     Returns:
       results - boolean if files were saved
    """
    results = False
    # query for folder name and create it
    dirName = input("\t Enter a directory name to create: ")
    # print("\n\t input directory name = <{}>".format(dirName))
    currentDir = os.getcwd()
    try:
        if dirName == "":
            print(
                "\t No directory specified, using current working directory: ",
                currentDir,
            )
        else:
            # create directory if it doesn't exist
            newDir = currentDir + "/" + dirName
            if not os.path.exists(newDir):
                os.mkdir(newDir)
            os.chdir(newDir)  # go to specified directory

        # get files and copy them into local directory
        for image in range(len(addedList)):
            success, fName = saveImageLocal(session, addedList[image])
            print("\t\t File: {} saved locally as {}".format(addedList[image], fName))

        os.chdir(currentDir)  # got back to where we started
        print("")  # give us some space on the responses
        results = True

    except FileExistsError:
        print("\t Error: could not create new directory " + newDir)
    except FileNotFoundError:
        # chdir() did not work or the path was not correct
        print("\t Error: unable to move into new directory " + newDir)

    return results


def saveImageLocal(session, resourcePath, apiURL=API_URL):
    """ Get an image from camera and save it locally

    Retrieve an image from camera and save it in the current directory.
    Saved file has same name as found in the resourcePath

    Inputs:
       session - Session object currently connected to camera
       resourcePath - CCAPI resource path of image to be fetched and saved
                 (i.e. /ccapi/ver130/contents/sd/111STRB3/IMG_7935.JPG )
       apiURL - domain and port URL

     Returns:
       success  - True or False based on if file was saved locally or not
       filename - Name of file saved (parsed from resourcePath)
    """
    success = False
    filename = ""
    result = getImage(session, resourcePath, apiURL)
    if result.status_code == 200:
        pathList = resourcePath.split("/")  # parse the resource
        filename = pathList[-1]
        with open(filename, "wb") as f:
            f.write(result.content)
        f.close()
        success = True
    else:
        print(
            "saveImageLocal: Error saving file ",
            resourcePath,
            " status_code=",
            result.status_code,
        )
        success = False

    return success, filename


def deleteImage(session, imagePath, apiURL=API_URL):
    """ Remove image from camera folder

    Delete an image and reports an error message if it was not able to
    delete it ( like it was protected, not a valid imagePath, ect)

    Inputs:
       session - Session object currently connected to camera
       imagePath - CCAPI resource path of image to be removed
                 (i.e. /ccapi/ver130/contents/sd/111STRB3/IMG_7935.JPG )
       apiURL - domain and port URL

     Returns:
       resp - response payload from CCAPI
    """
    response = sendR5CcapiDelete(session, imagePath, apiURL)
    if not response.status_code == 200:
        respDict = response.json()
        print("\t deleteImage: Error deleting ", imagePath)
        statusTxt = "\t deleteImage: statusCode={sc} message={msg}\n"
        print(statusTxt.format(sc=response.status_code, msg=respDict.get("message")))
    return response


# -------------------------------------
# Start general photographic utilities
# -------------------------------------


def depthOfField(dist=400, fStop=2.8, focalLen=100, coc=R5_COC):
    """ Determine Depth Of Field for camera/lens configuration.
    All distance args expected to be in millimeters
    Output returned in millimeters rounded to 2 decimal places

    dist = distance to subject in mm
    fStop = FStop setting
    focalLen = focal length of lens in mm
    coc = Circle Of Confusion value for camera sensor in mm (default Canon R5)
    """
    dof = (2 * math.pow(dist, 2) * fStop * coc) / math.pow(focalLen, 2)
    return round(dof, 3)


def stackingDOF(dof):
    """ Create an overlap of 80 percent of the depthOfField value for stacking images
    """
    return round(dof * 0.8, 2)  # increase rounding for better percision


def hyperfocalDistance(focalLen=100, fStop=4, coc=R5_COC):
    hfd = math.pow(focalLen, 2) / (coc * fStop)
    return round(hfd, 3)


def main():
    # test_1 - take picture
    r5Session, result = createR5Session()
    print("test_1: Session connected to camera: ", result)

    name, path = getCurrentDir(r5Session)
    print("test_1_dir: Directory_name=<", name, ">  Path=<", path, ">")

    numEntries, pageCnt = getNumDirEntries(r5Session, path)
    dirEntryText = "test_1_dir: path <{p}> has <{e}> entries with a page count of <{c}>"
    print(dirEntryText.format(p=path, e=numEntries, c=pageCnt))

    # test_2 - take a picture, report imageName, save locally,  delete image
    result = getLastEvent(r5Session)  # clear polling buffer in camera

    result = shootR5Image(session=r5Session, af=False)
    print("test_2: Image captured: ", result)

    time.sleep(1)  # must wait for image to be stored and poller to register it

    result = getLastEvent(r5Session)  # get all events from polling buffer
    addedList = result.get("addedcontents")  # only care about image(s) added
    print("test_2_addedImage: ", addedList)

    if not addedList == None:
        # status = saveImageLocal(r5Session, addedList[0])
        status = copyFiles(r5Session, addedList)
        print("test_2_localSave: file ", addedList[0], " saved: ", status)

        result = deleteImage(r5Session, addedList[0])
        print(
            "test_2_delete: image delete results = ", result.status_code
        )  # s/b 200 for success
    else:
        # polling via getLastEvent() doesn't always return saved file even through
        # is is saved on the camera. I believe this script runs faster than camera can
        # save image and update polling buffer. Might have investigate adding time delays
        print(
            "\n\tError: unable to get image name that got created from polling interface\n"
        )

    # test_3 - depthOfField()
    print(
        "test_3: DOF=",
        depthOfField(),
        " stacking DOF=",
        round((depthOfField() * 0.8), 2),
    )

    # test_4 - hyperfocalDistance()
    hyperFocalTxt = (
        "test_4: hyperfocal distance of {lens}mm lens at F {fstop} = {hfd}mm"
    )
    fstops = [2.8, 4, 5.6, 8, 11, 16, 22]
    for fstop in fstops:
        print(
            hyperFocalTxt.format(
                lens=100, fstop=fstop, hfd=hyperfocalDistance(fStop=fstop)
            )
        )


if __name__ == "__main__":
    main()
