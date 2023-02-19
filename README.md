# macroPhotoShooter

## Overview
Control Canon R5 camera wirelessly via Canon's CCAPI RESTful interface, and a 3D Printer bed serially via GCode/MCode to create multiple images for macrophotography. The printer bed acts as a slide for the subject while the camera stays still. The program determines the Depth Of Field based on user input, then controls the bed's Y-axis movement between camera captures.

Developed with:
|Program|Version|
|------|--------|
|Python|3.8.10|
|CCAPI| 1.3.0|

## My Setup
![my setup](images/macroSetup_1_300w.jpg) ![nut pic](images/dt_output2_1_104_300w.jpg)

The serial connection between my laptop and the **Anycubic I3 Mega** printer is USB. The printer supports Y-axis accuracy to 0.0125mm.

The Canon Camera Control API (CCAPI) interface is available via the [Canon Developer Community](https://developercommunity.usa.canon.com/s/). You must become a member of this community and they will supply a utility to activate the CCAPI on your supported Canon camera. (**Note:** Canon link is to Canon's USA community, you may have to find the community for your continent )

Code base was written in Python 3 and tested on Linux Mint 20.3

## File Info
- **macroPhotoShooter.py** - Main program. Establishes a connection to both printer and the R5. Prompts user to enter F-Stop, Lens focal length, Subject size, and Distance to Subject. Program determines the Depth of Field and computes the number of increments required to capture the entire subject. Program will loop between bed movement and image capture untill the required number of increments have been reached.
- **r5_cameraUtils.py** - Utilities controlling the R5 camera and image collection
- **gcodeUtils.py** - Utilities controlling 3D Printer and bed placement

## General Info
- All measurements are in millimeters - so much easier that way
- Subject images will be shot starting from front and working toward the back of the subject
- Camera should be in manual mode and prefocused on a spot on the subject **closest** to the camera
- Prior to the start of shooting, the bed will move away from focus point to ensure the closest point of the subject is captured
- As shooting progresses, the subject will move closer to the camera. Ensure your lighting stays consistent and shadows do not creep in unexpectedly
- Canon CCAPI does not currently allow creating folders to hold these images. Start each shooting session with a new folder on the camera to hold the images captured.

## Things to Do
 (no particular order)
- graphical frontend
- Checks to ensure subject length isn't too large for bed movement from current starting point
- Planning only option. Display various Depth of Field values and projected image counts for various F-Stop and subject lengths
- Lighting monitor. Precheck lighting conditions between starting and ending bed postions with the subject
- Move images from camera to computer (via CCAPI) for later image stacking
- Update code comments
