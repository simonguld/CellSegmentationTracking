<!-- Improved compatibility of back to top link: See: https://github.com/othneildrew/Best-README-Template/pull/73 -->
<a name="readme-top"></a>


<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/github_username/repo_name">
    <img src="images/logo.png" alt="Logo" width="80" height="80">
  </a>

<h3 align="center">project_title</h3>

  <p align="center">
    project_description
    <br />
    <a href="https://github.com/github_username/repo_name"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/github_username/repo_name">View Demo</a>
    ·
    <a href="https://github.com/github_username/repo_name/issues">Report Bug</a>
    ·
    <a href="https://github.com/github_username/repo_name/issues">Request Feature</a>
  </p>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

[![Product Name Screen Shot][product-screenshot]](https://example.com)

Here's a blank template to get started: To avoid retyping too much info. Do a search and replace with your text editor for the following: `github_username`, `repo_name`, `twitter_handle`, `linkedin_username`, `email_client`, `email`, `project_title`, `project_description`

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- GETTING STARTED -->
## Getting Started

This is an example of how you may give instructions on setting up your project locally.
To get a local copy up and running follow these simple example steps.

### Prerequisites

* Cellpose (in virtual environmate)
* Fiji -> trackmate-cellpose
* Java 8, Jython
* whatever packages I'm using (in a nice format? Possibly to allow pip install ...)
python 3.9

### Installation

1. Download and unpack the newest version of Fiji. Follow the instructions on https://imagej.net/software/fiji/downloads.
2. (??) Download and install Java 8 here: https://www.oracle.com/java/technologies/downloads/#java8-windows
3. Install the TrackMate extension Trackmate-Cellpose. To see how, visit: https://imagej.net/plugins/trackmate/detectors/trackmate-cellpose. Make sure to update it after installation.
4. Create a virtual enviroment called cellpose using Python 3.9 (it might also work with python 3.8 and 3.10). Follow the instructions on https://pypi.org/project/cellpose/. If you have a GPU available, consider installing the gpu-version; it drastically increases the segmentation speed
5. From the cellpose virtual environment, install CellSegmentationTracker using the following command:

   ```
   python -m pip install git+https://github.com/simonguld/CellSegmentationTracker.git
   ```
6. Now you should be good to go!

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- USAGE EXAMPLES -->
## Usage
* how to import
* documentation + link
* example_notebook
* images must be tif

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Pretrained models

## Documentation

### Importing the class
CellSegmentationTracker can be imported as follows:
```
from cellsegmentationtracker import CellSegmentationTracker
```

### Class definition


```
class CellSegmentationTracker.CellSegmentationTracker(self, imagej_filepath, cellpose_python_filepath,
 image_folder = None, xml_path = None, output_folder = None, use_model = 'CYTO',
custom_model_path = None, show_segmentation = False, cellpose_dict = {}, trackmate_dict = {}):
```
<<<<<<< HEAD

```
 __init__(self, imagej_filepath, cellpose_python_filepath, image_folder = None, xml_path = None,
output_folder = None, use_model = 'CYTO', custom_model_path = None, show_segmentation = False,
cellpose_dict = {}, trackmate_dict = {}):
```

**Parameters:**    
- **imagej_filepath** (str): The file path to the ImageJ/Fiji executable. It can be found in the Fiji.app folder
- **cellpose_python_filepath** (str): The file path to the Cellpose Python program. It can be found in the virtual environment created for running cellpose
- **image_folder** (str, default=None): The folder containing .tif input images for processing. If provided, the class will process all images within this folder. If not provided, an XML file must be provided instead, and the class methods can then be used for postprocess analysis
- **xml_path** (str, default=None): If segmentation and tracking has already been carried out, the resulting TrackMate XML file can be provided, and the class methods
can be used for postprocess analysis
- **output_folder** (str, default=None): The folder where output files will be saved. If not specified, the image folder (if provided) will be used and otherwise the XML folder. Note that XML files generated by the class will always be output to the image folder
- **use_model** (str, default='CYTO'): Specifies the Cellpose model to use for segmentation. Options include 'CYTO', 'CYTO2' and 'NUCLEI'.
- **custom_model_path** (str, default=None): If a custom Cellpose model is to be used, provide the path to the model here.
- **show_segmentation** (bool, default=True): Determines whether to open Fiji and display the segmentation results interactively during processing.
- **cellpose_dict** (dict, default=dict()): A dictionary containing additional parameters to pass to the Cellpose segmentation algorithm listed below:
  - TARGET_CHANNEL (positive int, default = 0): What channel to use as the main channel for segmentation with cellpose. ‘0’ means that cellpose will run on a grayscale combination of all channels. ‘1’ stands for the first channel, corresponding to the red channel in a RGB image. Similarly for ‘2’ and ‘3’, the second and third channel, corresponding to the green and blue channels in a RGB image.
  - OPTIONAL_CHANNEL_2 (positive int, default = 0): The cyto and cyto2 pretrained models have been trained on images with a second channels in which the cell nuclei were labeled. It is used as a seed to make the detection of single cells more robust. It is optional and this parameter specifies in which channel are the nuclei (‘1’ to ‘3’). Use ‘0’ to skip using the second optional channel. For the nuclei model, this parameter is ignored.
  - CELL_DIAMETER (positive int, default = 0): Estimate of the cell diameter in the image, in physical units. Enter the value ‘0’ to have cellpose automatically determine the cell size estimate.
  - USE_GPU (boolean, default = False)
  - SIMPLIFY_CONTOURS (boolean, default = True): If True the 2D contours detected will be simplified. If False, they will follow exactly the pixel borders.
- **trackmate_dict** (dict, default=dict()): A dictionary containing parameters for configuring the TrackMate LAPTracker. It has the following keys:
    - LINKING_MAX_DISTANCE (float, default = 15.0): The max distance between two consecutive spots, in pixel units, allowed for creating links.
    - GAP_CLOSING_MAX_DISTANCE (float, default = 15.0): Gap-closing max spatial distance. The max distance between two spots, in physical units, allowed for creating links over missing detections. 
    - MAX_FRAME_GAP (positive int, default = 2): Gap-closing time-distance. The max difference in time-points between two spots to allow for linking. For instance a value of 2 means that the tracker will be able to make a link between a spot in frame t and a successor spots in frame t+2, effectively bridging over one missed detection in one frame. 
    - ALLOW_TRACK_MERGING (bool, default = True): If True then the tracker will perform tracklets or segments merging, that is: have two or more tracklet endings linking to one tracklet beginning. This leads to tracks possibly fusing together across time.
    - ALLOW_TRACK_SPLITTING (bool, default = True): If True then the tracker will perform tracklets or segments splitting, that is: have one tracklet ending linking to two or more tracklet beginnings . This leads to tracks possibly separating into several sub-tracks across time, like in cell division.                 

**Methods:**

**Attributes:**


<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE.txt` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTACT -->
## Contact

Your Name - [@twitter_handle](https://twitter.com/twitter_handle) - email@email_client.com

Project Link: [https://github.com/github_username/repo_name](https://github.com/github_username/repo_name)

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

* []()
* []()
* []()

<p align="right">(<a href="#readme-top">back to top</a>)</p>
=======

