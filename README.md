# macroPhotoShooter

## Overview
Control Canon R5 camera wirelessly via Canon's CCAPI RESTful interface, and a 3D Printer bed serially via GCode/MCode to create multiple images for macrophotography. The printer bed acts as a slide for the subject while the camera stays still.
 The program determines the Depth Of Field based on user input, then controls the bed's Y-axis movement between camera automatic captures. All images captured can be transfered wirelessly to a local file directory. Original images are kept on camera medium.
 Stacking of images is not performed by this program. One option is to use my [photoStacker script](https://github.com/poolsidebill/photoStacker), but plenty of other options exist.

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

## Menu Options

|Number|Name|Description|
|------|----|-----------|
|1  |Printer Status|Check or establish 3D printer connection and control. Homes printer bed and optionally moves Z-axis out of the way of the picture area|
|2  |Camera Status   | Check or establish camera control. Reports battery atatus to confirm  RESTful CCAPI is working  |
|3  |Define Shot Parameters   |Define parameters of **camera** (fstop and lens focal length) and **subject** (size and distance to camera focal plane). This information is used to determine the number of images required to capture the subject at current Depth Of Field and bed movement between each shot   |
|4 | Check Shot Endpoints   | Specify Front-to-Back or Back-to-Front shooting direction. Bed is moved between first and last shooting position (as determined in option 3) allowing user to check lighting and framing of subject  |
|5 |Perform Shot Captures   | Automatic control of bed movement and camera to capture the number of images (defined via option 3) required. Images captured can then be transfered from camera to a local directory for further processing (i.e. stacking). Transfering of images is controlled by a prompt. Original images will always remain on the camera  |
|6   |Print Bed Location   | Queries the printer for current X, Y, Z axis locations and displays the results  |
|7   | Change Z-axis  | Move Z axis on printer. Prompts for direction and distance to move the Z axis. Used to manually adjust postion of Z axis. Just a feature that comes in handy when you need it  |
|8   | Exit  |Leave this program  |

## General Info
- All measurements are in millimeters - so much easier that way
- Camera should be in manual mode and prefocused on a spot on the subject
- As a default, subject images will be shot starting from front and working toward the back of the subject
    - Front to Back shooting - suggested normal subject size
    - Back to Front shooting - suggested for larger subject size
    - Shooting direction can be changed under menu option **4 - Check Shot Endpoints**
- As shooting progresses, the subject will move closer or further from to the camera based on the shooting direction described above. Ensure your lighting stays consistent and shadows do not creep in unexpectedly
    - Check lighting and image composition with menu option **4 - Check Shot Endpoints**
- Canon CCAPI does not currently allow creating folders to hold these images. Start each shooting session with a new folder on the camera to hold the images captured.

## Things to Do
 (no particular order)
- graphical frontend
- Checks to ensure subject length isn't too large for bed movement from current starting point
- Save shot parameters to file for macro shot history
- Planning only option. Display various Depth of Field values and projected image counts for various F-Stop and subject lengths
- **Added 30Mar23** ~~Lighting monitor. Precheck lighting conditions between starting and ending bed postions with the subject~~
- **Added 08Mar23** ~~Move images from camera to computer (via CCAPI) for later image stacking~~
- Update code comments
