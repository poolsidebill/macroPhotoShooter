""" r5_cameraUtils.py
    bcase 02Feb2023
    Helpful Canon R5 functions
"""
import sys, traceback
import requests
from requests.exceptions import Timeout
import time
import math

# Constants
API_URL = "http://192.168.1.188:8080"

R5_COC = 0.00439 # pixelsize of R5 sensor

def createR5Session():
    """ A single session for all requests keeps multiple connection requests
      from being refused by the camera
      Supressing full traceback, will print top-level exception
    """
    success = False
    try:
      sys.tracebacklimit = 10 # only the exception type and value are printed
      session = requests.Session()
      print("initial CCAPI session response: ",session.get(API_URL+"/ccapi", timeout=(2,5))) #establish inital connection
      success = True
    except Exception as e:
        print("Exception detected in createR5Session")
        print(e)
        # print("-"*60)
        # traceback.print_exc(file=sys.stdout)
        # print("-"*60)

    return session, success

def sendR5CcapiCmd(session, resource, cmdData, apiURL=API_URL):
    resp = {}
    try:
        resp = session.post(apiURL+resource, json=cmdData, timeout=(2,5))
        #print(resp)
    except requests.exceptions.Timeout as errt:
        print("\t Timeout happened on request",errt)
    except requests.exceptions.ConnectionError as errc:
        print("\t", errc)

    return resp

def decodeR5CcapiResponse(resp):
    respDict =  resp.json()
#    print("CCAPI response items: ", respDict.items()) # all key:value pairs
    print("decodeR5CcapiResponse: ", respDict.get("message"))

def shootR5Image(session, apiURL=API_URL, af=True):
    """ Capture a single picture image on the R5
    Handles rety if the camera is busy (i.e. storing a previous picture)
    """
    CTRL_BTN = "/ccapi/ver100/shooting/control/shutterbutton/manual"
    PRESS_PRAM = {"action": "full_press","af": True}
    RELEASE_PRAM = {"action": "release", "af": True}

    success = False
    paramDict=PRESS_PRAM
    if not af:
      paramDict["af"] = False

    while True:
      result = sendR5CcapiCmd(session, resource=CTRL_BTN, cmdData=PRESS_PRAM)  # press shutter button
      #print("cmd sent. result:",result.status_code)
      print("cmd sent. result:",result)
      time.sleep(.15)
      if result == {}:
          return success  # serious error
      elif not result.status_code == 503: # retry loop if camera is busy
          break

    # command was accepted, check its status
    if result and result.status_code == 200:
        result = sendR5CcapiCmd(session, resource=CTRL_BTN, cmdData=RELEASE_PRAM)  # release shutter button
        if result and result.status_code == 200:
            # Success
            print("Camera image captured")
            success = True
        else:
            print("Camera command to release shutter button failed")
            decodeR5CcapiResponse(response)
    else:
        print("Camera command to press shutter button failed.",result)
        decodeR5CcapiResponse(result)

    return success

def depthOfField(dist=400, fStop=2.8,focalLen=100, coc=R5_COC ):
    """ Determine Depth Of Field for camera/lens configuration.
    All distance args expected to be in millimeters
    Output returned in millimeters rounded to 2 decimal places

    dist = distance to subject in mm
    fStop = FStop setting
    focalLen = focal length of lens in mm
    coc = Circle Of Confusion value for camera sensor in mm (default Canon R5)
    """
    dof = (2*math.pow(dist,2)*fStop*coc)/math.pow(focalLen,2)
    return round(dof,2)

def stackingDOF(dof):
    return round(dof*0.8, 1)

def hyperfocalDistance(focalLen=100, fStop=4, coc=R5_COC):
    hfd = math.pow(focalLen,2)/(coc*fStop)
    return round(hfd,3)

def main():
    # test_1 - take picture
    r5Session, result = createR5Session()
    print("test_1: Session connected to camera: ", result)

    # test_2 - take a picture
    result = shootR5Image(session=r5Session, af=False)
    print("test_2: Image captured: ", result)

    # test_3 - depthOfField()
    print("test_3: DOF=",depthOfField()," stacking DOF=",round((depthOfField()*.8),2))

    # test_4 - hyperfocalDistance()
    hyperFocalTxt = "test_4: hyperfocal distance of {lens}mm lens at F {fstop} = {hfd}mm"
    fstops = [2.8, 4, 5.6, 8, 11, 16, 22]
    for fstop in fstops:
      print(hyperFocalTxt.format(lens=100, fstop=fstop, hfd=hyperfocalDistance(fStop=fstop)))

if __name__ == "__main__":
    main()
