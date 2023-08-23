## Author: Simon Guldager Andersen

## Imports:
import os
import sys
import json
import time
import warnings
from subprocess import Popen, PIPE


import numpy as np
import seaborn as sns
import pandas as pd
import xml.etree.ElementTree as et

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import matplotlib.animation as ani
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib import rcParams
from cycler import cycler

from utils import trackmate_xml_to_csv, merge_tiff, get_imlist, prepend_text_to_file, search_and_modify_file


## Set plotting style and print options
sns.set_theme()
sns.set_style("darkgrid")
sns.set_context("paper") #Possible are paper, notebook, talk and poster

d = {'lines.linewidth': 2, 'axes.titlesize': 18, 'axes.labelsize': 18, 'xtick.labelsize': 12, 'ytick.labelsize': 12,\
     'legend.fontsize': 15, 'font.family': 'serif', 'figure.figsize': (9,9)}
d_colors = {'axes.prop_cycle': cycler(color = ['teal', 'navy', 'coral', 'plum', 'purple', 'olivedrab',\
         'black', 'red', 'cyan', 'yellow', 'khaki','lightblue'])}
rcParams.update(d)
rcParams.update(d_colors)
np.set_printoptions(precision = 5, suppress=1e-10)





##TODO:

##ESSENTIAL (DO FIRST)

##EST: 30 min
# 1) TEST: Prøv modeller af på de forskellige datasæt. virker DET?
# 11) compare velocties to trackmate speed
## fix.. sample images....
## LAV DATAGUF TIL NATASCHA

# 2) Impl. grid analysis, incl saving and plotting
### document
# 3) Impl. density fluctuations
# --> (inkl fix impl.) 
# -->[allow plotting rel. to av cell number also?]
# --> allso number density vs denisty
## TEST TEST TEST And read trough to get rid of errors
# --> dur det på big data?

# pixels --> physical if provided. ALSP (unit dict?)

# 6) Documents methods, attributes, class in readme and script
# 7) Finish README
# 8) Finish example notebook (possibly: allow for im_path to be hyperlink)
# 9) Make sure package works INCLUDING FIX utiils --> cellsegmentationtracker.utils.
# 10) test it by making new venc



# EFTER SEND-OFF:

### METHODS: 
# MSD and CRMSD
# Nearest neighbors estimator?
# Tas' method
# vorticity???
# try on nuclei data. works?

### HANDLING UNITS:
# input pixel_height=physical unit, pixel_width=physical unit, frame_interval=physical unit
# CHECK XML TO see if time and lengths are provided. otherwise print info message
# ALSO possbily allow entering physical units
# NBNBNB: Velocities depend on it!

### ATTRIBUTES
# allow for user providing csvs????
# make a print all features method
# possibly extend grid analysis to include all features

### VISUALIZATION
# SPEND A LITTLE TIME ON:
# make show_tracks opt?
# fix cellmask color if possible(se på features/featureutils.java)

### RUN-SPPED
# CONSIDER:
# not loading all features to csv
#  2) not calculating everything in trackmate 
# 3) resizing input 


## NONESSENTIAL (IF TIME)
# include the resize/splitting stuff (Resizing must preserve rel. proportions. ALSO: alters the observables. Take into account)
# train nuclei data. NB: 1 bad img
# make naming of xml and csv files more flexible
# make roubst under other image formats?
# make robust under color, multichannel etc?


class CellSegmentationTracker:

    """
    Documentation for CellSegmentationTracker class.
    """

    def __init__(self, imagej_filepath = None, cellpose_python_filepath = None, image_folder_path = None, xml_path = None, output_folder_path = None,
                  use_model = 'CYTO', custom_model_path = None, show_segmentation = True, cellpose_dict = dict(), trackmate_dict = dict()):

        self.imagej_filepath = imagej_filepath
        self.cellpose_python_filepath = cellpose_python_filepath
        self.img_folder = image_folder_path
        self.img_path = None
        self.xml_path = xml_path     
        self.custom_model_path = custom_model_path
        self.__working_dir = os.getcwd()
        self.__class_path = os.path.dirname(os.path.realpath(__file__))
        self.__parent_dir = os.path.abspath(os.path.join(self.__class_path, os.pardir))
        self.__fiji_folder_path = os.path.dirname(self.imagej_filepath) if self.imagej_filepath is not None else None

        if self.cellpose_python_filepath is not None:
            self.__cellpose_folder_path = os.path.join(os.path.dirname(self.cellpose_python_filepath), 'Lib', 'site-packages', 'cellpose')
            self.pretrained_models_paths = [os.path.join(self.__cellpose_folder_path, 'models', 'cyto_0'), \
                                        os.path.join(self.__cellpose_folder_path, 'models', 'cyto_1'),\
                                        os.path.join(self.__cellpose_folder_path, 'models', 'nuclei'), \
                                        os.path.join(self.__parent_dir, 'models', 'epi500'), \
                                        os.path.join(self.__parent_dir, 'models', 'epi2500'), \
                                            os.path.join(self.__parent_dir, 'models', 'epi6000')]
        else:
            self.__cellpose_folder_path = None
            self.pretrained_models_paths = None
        
        # Set output folder path to image folder path, if not provided, and to current path if image folder path is not provided
        if output_folder_path is None:
            if self.img_folder is not None:
                self.output_folder = self.img_folder if os.path.isdir(self.img_folder) else os.path.dirname(self.img_folder)
            else:
                self.output_folder = self.__working_dir
        else:
            self.output_folder = output_folder_path

        self.use_model = use_model
        self.show_segmentation = show_segmentation
        self.cellpose_dict = cellpose_dict
        self.trackmate_dict = trackmate_dict
        self.jython_dict = {}

        self.flow_threshold = None
        self.cellprob_threshold = None
        self.spots_df = None
        self.tracks_df = None
        self.edges_df = None
        self.grid_df = None

        self.pretrained_models = ['CYTO', 'CYTO2', 'NUCLEI', 'EPI500', 'EPI2500', 'EPI6000']

        self.cellpose_default_values = {
            'TARGET_CHANNEL' : 0,
            'OPTIONAL_CHANNEL_2': 0,
            'CELLPOSE_PYTHON_FILEPATH': self.cellpose_python_filepath,
            'CELLPOSE_MODEL': self.use_model,
            'FLOW_THRESHOLD': 0.4,
            'CELLPROB_THRESHOLD': 0.0,
            'CELL_DIAMETER': 0.0,
            'USE_GPU': False,
            'SIMPLIFY_CONTOURS': True
            }
        self.trackmate_default_values = {'LINKING_MAX_DISTANCE': 15.0,
                                         'GAP_CLOSING_MAX_DISTANCE': 15.0,
                                         'MAX_FRAME_GAP': 2,
                                         'ALLOW_TRACK_SPLITTING': False,
                                         'ALLOW_TRACK_MERGING': False,
             }

        self.__grid_dict = {'xmin': None, 'ymin': None, \
                          'xmax': None, 'ymax': None, \
                        'Nx': None, 'Ny': None, \
                            'grid_len': None, 'Nsquares': None, 
                            'Lx': None, 'Ly': None
                            }

        self.Nspots = None
        self.Ntracks = None
        self.Nframes = None


    #### Private methods ####

    def __prepare_images(self):
        """
        Prepare images for cellpose segmentation.
        """
        # If no image folder is provided, raise error
        if self.img_folder is None:
            raise OSError("No image folder nor xml file provided!")
        # If image folder is provided, check if it is a folder or a .tif file
        elif self.img_folder[-4:] != ".tif" and not os.path.isdir(self.img_folder):
            raise OSError("Image folder path must either be a folder or a .tif file!")
        # If .tif file is provided instead of folder, handle it
        elif self.img_folder[-4:] == ".tif":
            self.img_path = self.img_folder
            self.img_folder = os.path.dirname(self.img_folder)
        else:
            im_list = get_imlist(self.img_folder, '.tif')
            # If more than one .tif file is provided, merge them into one
            if len(im_list) > 1:
                # Make sure that such a file has not already been created    
                self.img_path = os.path.join(self.img_folder, "merged.tif")
                if os.path.isfile(self.img_path):
                    os.remove(self.img_path)
                merge_tiff(self.img_folder, img_out_name = os.path.join(self.img_folder, "merged.tif"))
                print("\nMerged tif files into one file: ", self.img_path)
            else:
                self.img_path = im_list[0]
                print("\nUsing tif file: ", self.img_path)
        return

    def __modify_cellpose(self):
        """
        Modify cellpose source code to allow for modification of flow and cell probability threshold.
        """
        # Define paths to files to modify
        paths_to_modify = [os.path.join(self.__cellpose_folder_path, name) for name in ['models.py', 'dynamics.py', 'cli.py']]

        # Define search and replace strings
        search_strings = ["'--flow_threshold', default=0.4", "'--cellprob_threshold', default=0", \
                      'flow_threshold=0.4', 'cellprob_threshold=0.0',  \
                      'flow_threshold= 0.4', 'flow_threshold = 0.4', \
                        'cellprob_threshold= 0.0', 'cellprob_threshold = 0.0' ]
        replace_strings = ["'--flow_threshold', default=flow_param", "'--cellprob_threshold', default=cellprop_param", \
                          'flow_threshold=flow_param', 'cellprob_threshold=cellprop_param', \
                            'flow_threshold= flow_param', 'flow_threshold = flow_param', \
                            'cellprob_threshold= cellprop_param', 'cellprob_threshold = cellprop_param' ]

        # Define message to prepend to file to allow for modification of flow and cell probability threshold
        msg = f"\nimport numpy as np\nimport os\ndir = os.path.dirname(os.path.abspath(__file__))\nflow_param, cellprop_param = np.loadtxt(os.path.join(dir, 'params.txt')) \n\n"  

        # Modify files
        for p in paths_to_modify:
            prepend_text_to_file(p, msg)
            for search_string, replace_string in zip(search_strings, replace_strings):
                search_and_modify_file(p, search_string, replace_string)
        print("Cellpose source code files have been modified to allow for modification of flow and cell probability threshold.")
        return

    def __generate_jython_dict(self):
        """
        Generate the dictionary holding the parameters needed to run the jython script.
        """
        # Specify paths and whether to show segmentation
        self.jython_dict.update({"IMG_PATH": self.img_path, "FIJI_FOLDER_PATH": self.__fiji_folder_path, \
                                    "CELLPOSE_PYTHON_FILEPATH": self.cellpose_python_filepath,
                                    "OUTPUT_PATH": self.output_folder, "SHOW_SEGMENTATION": self.show_segmentation})

        # Specify Cellpose and TrackMate parameters not set by user
        if self.cellpose_dict == {}:
            self.cellpose_dict = self.cellpose_default_values
            del self.cellpose_dict['FLOW_THRESHOLD']
            del self.cellpose_dict['CELLPROB_THRESHOLD']
        else:
            for key in set(self.cellpose_default_values) - set(['FLOW_THRESHOLD', 'CELLPROB_THRESHOLD']):
                if key not in self.cellpose_dict.keys():
                    self.cellpose_dict[key] = self.cellpose_default_values[key]
        if self.trackmate_dict == {}:
            self.trackmate_dict = self.trackmate_default_values
        else:
            for key in self.trackmate_default_values.keys():
                if key not in self.trackmate_dict.keys():
                    self.trackmate_dict[key] = self.trackmate_default_values[key]
        self.cellpose_dict['CELLPOSE_MODEL_FILEPATH'] = self.custom_model_path

        self.jython_dict.update({'CELLPOSE_DICT': self.cellpose_dict})
        self.jython_dict.update({'TRACKMATE_DICT': self.trackmate_dict}) 

        # Warn user about track merging and splitting
        if self.trackmate_dict['ALLOW_TRACK_MERGING'] or self.trackmate_dict['ALLOW_TRACK_SPLITTING']:
            print("\nWARNING: Track merging and/or splitting has been allowed. This may result in inconsistent velocities, \
                  as more spots belonging to the same track can be present at the same time\n")

        return

    def __run_jython_script(self):
        """
        Run the jython script by calling the command line.
        """
        # Change directory to fiji folder
        os.chdir(self.__fiji_folder_path)
        # Get name of executable
        executable = list(os.path.split(self.imagej_filepath))[-1]
        # Set path to jython script
        jython_path = os.path.join(self.__class_path, "jython_cellpose.py")

        if self.show_segmentation:
            try: 
                command = executable + ' --ij2 --console --run "' + jython_path + '"'
                os.system(command)
            except: 
                KeyboardInterrupt
                sys.exit(0)
        else:
            self.xml_path = self.img_path.strip(".tif") + ".xml"
        
            # To run headlessly, call jython script as a subprocess
            pipe = Popen([executable,'--ij2','--headless', '--run', f"{jython_path}"], stdout=PIPE)
            # wait for xml file to be created
            try:
                while not os.path.isfile(self.xml_path):
                    time.sleep(3)
                    continue
            except: 
                KeyboardInterrupt
                sys.exit(0)
            # kill subprocess
            pipe.kill()
            # print output
            print(pipe.communicate()[0].decode('ascii'))
            
        # Change directory back to current one
        os.chdir(self.__working_dir)    
        return
    
    def __initialize_grid(self, Ngrid):
        """
        Initialize grid dictionary.
        """
  
        # Extract relevant data from dataframe as array
        cols = ['Frame', 'X', 'Y']
        data = self.spots_df.loc[:, cols].values.astype('float')

        # Create empty array to store grid data
        self.Nframes = int(data[:,0].max() + 1)
        
        self.__grid_dict['xmin'], self.__grid_dict['xmax'] = data[:,1].min(), data[:,1].max()
        self.__grid_dict['ymin'], self.__grid_dict['ymax'] = data[:,2].min(), data[:,2].max()

        self.__grid_dict['Lx'] = self.__grid_dict['xmax'] - self.__grid_dict['xmin']
        self.__grid_dict['Ly'] = self.__grid_dict['ymax'] - self.__grid_dict['ymin']
   
        # Calculate number of grid squares in x and y direction
        if self.__grid_dict['Lx'] > self.__grid_dict['Ly']:
            self.__grid_dict['Ny'] = Ngrid
            self.__grid_dict['Nx'] = int(np.floor(Ngrid * self.__grid_dict['Lx'] / self.__grid_dict['Ly']))
            self.__grid_dict['grid_len'] = self.__grid_dict['Ly'] / self.__grid_dict['Ny']
            Residual_x = self.__grid_dict['Lx'] % self.__grid_dict['grid_len']
            self.__grid_dict['xmin'] = self.__grid_dict['xmin'] + Residual_x / 2
            self.__grid_dict['xmax'] = self.__grid_dict['xmax'] - Residual_x / 2
        elif self.__grid_dict['Lx'] <= self.__grid_dict['Ly']:
            self.__grid_dict['Nx'] = Ngrid
            self.__grid_dict['Ny'] = int(np.floor(Ngrid * self.__grid_dict['Ly'] / self.__grid_dict['Lx']))
            self.__grid_dict['grid_len'] = self.__grid_dict['Lx'] / self.__grid_dict['Nx']
            Residual_y = self.__grid_dict['Ly'] % self.__grid_dict['grid_len']
            self.__grid_dict['ymin'] = self.__grid_dict['ymin'] + Residual_y / 2
            self.__grid_dict['ymax'] = self.__grid_dict['ymax'] - Residual_y / 2

        self.__grid_dict['Nsquares'] = self.__grid_dict['Nx'] * self.__grid_dict['Ny']
        return
    
    def __heatmap_plotter(self, i, frame, feature, vmin, vmax, title=None):
        """
        Plots a heatmap of the given feature for a given frame.
        """  
        arr_grid = frame.reshape(self.__grid_dict['Ny'], self.__grid_dict['Nx'])

        xticklabels = np.round(np.linspace(self.__grid_dict['xmin'], self.__grid_dict['xmax'], 4) + self.__grid_dict['grid_len'] / 2, 2) 
        yticklabels = np.round(np.linspace(self.__grid_dict['ymax'], self.__grid_dict['ymin'], 4) + self.__grid_dict['grid_len'] / 2, 2)

        ax = sns.heatmap(arr_grid, cmap = 'viridis', vmin=vmin, vmax=vmax)

        title = f'{feature.capitalize()} heatmap for frame = {i}' if title is None else title
        ax.set(xlabel = 'x', ylabel = 'y', title = title)
        ax.set_xticks(ticks = np.linspace(0.5,self.__grid_dict['Nx'] - 0.5, 4), labels=xticklabels)
        ax.set_yticks(ticks = np.linspace(0.5, self.__grid_dict['Ny'] - 0.5, 4), labels=yticklabels)
        return

    def __velocity_field_plotter(self,X, Y, VX, VY, i = 0, title = None):
        """
        Plot the velocity field for a given frame.
        """
        title = f'Velocity field for frame = {i}' if title is None else title

        print("VX\n")
        print(VX)
        print("VY\n")
        print(VY)

        plt.quiver(X, Y, VX, VY, units='dots', scale_units='dots' )
        plt.xlabel(xlabel = 'x')
        plt.ylabel(ylabel = 'y')
        plt.title(title)
  
        return

    def __velocity_streamline_plotter(self, X, Y, VX, VY, i = 0, title = None):
        """
        Plot the velocity streamlines for a given frame.
        """
        title = f'Velocity streamlines for frame = {i}' if title is None else title

        plt.streamplot(np.unique(X), np.unique(Y), np.flip(VX, axis = 0), np.flip(VY, axis = 0), density = 1.5, color = 'black', linewidth=1, arrowsize=1)
        plt.xlabel(xlabel = 'x')
        plt.ylabel(ylabel = 'y')
        plt.title(title)
        return

    def __animate_flow_field(self, i, X, Y, arr, fig, fn,):
        """
        Animate the flow field for a given frame. Used as a wrapper for the animator function.
        """

        # we want a fresh figure everytime
        fig.clf()
        # add subplot, aka axis
        # load the frame
        arr_vx = arr[arr[:, 0] == i][:, -2].reshape(self.__grid_dict['Ny'], self.__grid_dict['Nx'])
        arr_vy = arr[arr[:, 0] == i][:, -1].reshape(self.__grid_dict['Ny'], self.__grid_dict['Nx'])
        # call the global function
        fn(X, Y, arr_vx, arr_vy, i=i)
        return
        
    def __animator(self, arr, fn, rng, animate_wrapper = None, inter=200, show=True):
        """Show a frame-by-frame animation.

        Parameters:
        arr -- the data array
        fn -- the plot function (argument: fram number, frame)
        rng -- range of the frames to be plotted
        animate_wrapper -- wrapper function for the animation function
        inter -- time between frames (ms)
        show -- whether to show the animation
        """

        # create the figure
        fig = plt.figure()

        if animate_wrapper is None:
            # the local animation function
            def animate_fn(i):
                # we want a fresh figure everytime
                fig.clf()
                # add subplot, aka axis
                #ax = fig.add_subplot(111)
                # load the frame
                frame = arr[arr[:, 0] == i][:, -1]
                # call the global function
                fn(i, frame)
        else:
            animate_fn = lambda i: animate_wrapper(i, arr, fig, fn)
                
        anim = ani.FuncAnimation(fig, animate_fn,
                                frames=np.arange(rng[0], rng[1]),
                                interval=inter, blit=False)
        if show==True:
            plt.show()
        return

    
    #### Public methods ####

    def run_segmentation_tracking(self):
        """
        Run cellpose segmentation and trackmate tracking.
        """
        # Ensure that imageJ filepath is valid
        if not os.path.isfile(self.imagej_filepath):
            raise OSError("Invalid imageJ filepath!")
        # Ensure that cellpose python filepath is valid
        if not os.path.isfile(self.cellpose_python_filepath):
            raise OSError("Invalid cellpose python filepath!")
        # Ensure that image folder/file path is valid
        if not os.path.isdir(self.img_folder) and not os.path.isfile(self.img_folder):
            raise OSError("Invalid image folder path!")
        
        ## Set relevant attribute values
        # Extract or set flow and cell probability threshold
        try:
            self.flow_threshold = self.cellpose_dict['FLOW_THRESHOLD']
            del self.cellpose_dict['FLOW_THRESHOLD']
        except:
            if self.use_model == 'EPI2500':
                self.flow_threshold = 0.6
            elif self.use_model == 'EPI6000':
                self.flow_threshold = 0.5
            else:
                self.flow_threshold = 0.4
        try:
            self.cellprob_threshold = self.cellpose_dict['CELLPROB_THRESHOLD']
            del self.cellpose_dict['CELLPROB_THRESHOLD']
        except:
            if self.use_model == 'EPI2500':
                self.cellprob_threshold = -1
            elif self.use_model == 'EPI500':
                self.cellprob_threshold = 0.5
            else:
                self.cellprob_threshold = 0.0

        # Set model path
        if self.custom_model_path is not None:
            self.use_model = 'CUSTOM'

        # If custom model is not provided, find the path of the pretrained model
        if self.custom_model_path is None and self.use_model not in self.pretrained_models:
            raise ValueError("No custom model path provided, and use_model not in pretrained models: ", self.pretrained_models)
        elif self.custom_model_path is None and self.use_model in self.pretrained_models:
            idx = self.pretrained_models.index(self.use_model)
            self.custom_model_path = self.pretrained_models_paths[idx]
        

        # Prepare images
        self.__prepare_images()

        # Ensure that xml file has not already been created
        if os.path.isfile(self.img_path.strip(".tif") + ".xml"):
            print("Skipping segmentation and tracking, as xml file already exits at: ", self.img_path.strip(".tif") + ".xml")
        else:
            # Generate dictionary for jython script
            self.__generate_jython_dict()

            # If not already done, modify cellpose source code to allow for modification of flow and cell probability threshold
            if not os.path.isfile(os.path.join(self.__cellpose_folder_path, 'params.txt')):
                self.__modify_cellpose()

            # Save flow and cell probability threshold to txt file
            np.savetxt(os.path.join(self.__cellpose_folder_path, 'params.txt'), \
                        np.array([self.flow_threshold, self.cellprob_threshold]))
            
            # Save dictionary to json file
            with open(os.path.join(self.__class_path,"jython_dict.json"), 'w') as fp:
                json.dump(self.jython_dict, fp)

            # Run jython script
            self.__run_jython_script()

            # Reinclude flow_threshold and cellprob in cellpose dict 
            self.cellpose_dict.update({'FLOW_THRESHOLD': self.flow_threshold, 'CELLPROB_THRESHOLD': self.cellprob_threshold})

            # Reset flow and cell probability threshold to default values after run
            np.savetxt(os.path.join(self.__cellpose_folder_path, 'params.txt'), \
                        np.array([0.4, 0.0]))
            
        # Set xml path to image path
        self.xml_path = self.img_path.strip(".tif") + ".xml"
        return

    def generate_csv_files(self, calculate_velocities = True, get_tracks = True, \
                           get_edges = True, save_csv_files = True, name = None):
        """
        Generate spot, track and edge dataframes from xml file, with the option of saving them to csv files.

        Parameters:
        -----------
        calculate_velocities : (bool, default = True) - whether to calculate velocities from trackmate data and
                                include them in the spots csv file
        get_tracks : (bool, default = True) - whether to generate a dataframe with track features
        get_edges : (bool, default = True) - whether to generate a dataframe with edge features
        save_csv_files : (bool, default = True) - whether to save the csv files to the output folder
        name : (str, default = None) - name of csv files. If None, the name of the image file is used.


        """
        if self.xml_path is not None:
            print("\nStarting to generate csv files from xml file now. This may take a while... \
                  \nProcessing an XML file with 120.000 spots, 90.000 edges and 20.000 tracks takes about 6-7 minutes to process on a regular laptop.\n")
                  

            self.spots_df, self.tracks_df, self.edges_df = trackmate_xml_to_csv(self.xml_path, calculate_velocities=True,
                                                            get_track_features = get_tracks, get_edge_features = get_edges)
        else:
            raise OSError("No xml file provided!")
        
        self.Nspots = len(self.spots_df)
        self.Ntracks = len(self.tracks_df)
        self.Nframes = self.spots_df['Frame'].max() + 1

        if save_csv_files:
            self.save_csv(name)
        return

    def get_feature_keys(self):
        """
        Get the keys of the features in the csv files.
        """
        if self.spots_df is not None:
            print("Spot features: ", self.spots_df.columns)
        if self.tracks_df is not None:
            print("Track features: ", self.tracks_df.columns)
        if self.edges_df is not None:
            print("Edge features: ", self.edges_df.columns)
        return

    def save_csv(self, name = None):
        """
        Save csv files to output folder.

        Parameters:
        -----------
        name : (str, default = None) - name of csv files. If None, the name of the image file is used.

        """
        if name is None:
            try:
                name = os.path.basename(self.img_path).strip(".tif")
            except:
                name = 'CellSegmentationTracker'

        if self.spots_df is not None:
            path_out_spots = os.path.join(self.output_folder, name + '_spots.csv')
            self.spots_df.to_csv(path_out_spots, sep = ',') 
            print("Saved spots csv file to: ", path_out_spots)
        if self.tracks_df is not None:
            path_out_tracks = os.path.join(self.output_folder, name + '_tracks.csv')
            self.tracks_df.to_csv(path_out_tracks, sep = ',') 
            print("Saved tracks csv file to: ", path_out_tracks)
        if self.edges_df is not None:
            path_out_edges = os.path.join(self.output_folder, name + '_edges.csv')
            self.edges_df.to_csv(path_out_edges, sep = ',')
            print("Saved edges csv file to: ", path_out_edges)
        return

    def print_settings(self):
        """
        Print the settings used for cellpose segmentation and trackmate tracking, as well as some
        basic image information.
        """

        root = et.fromstring(open(self.xml_path).read())

        im_settings = root.find('Settings').find('ImageData')
        basic_settings = root.find('Settings').find('BasicSettings')

        im_settings_list = ['filename', 'folder', 'width', 'height', 'nslices', 'nframes', 'pixelwidth', 'pixelheight', 'voxeldepth','timeinterval']
        basic_settings_list = ['xstart', 'xend', 'ystart', 'yend', 'zstart', 'zend', 'tstart', 'tend']
        settings = [im_settings_list, basic_settings_list]

        print_list = []
        for i, obj in enumerate([im_settings, basic_settings]):
            settings_list = settings[i]      
            for  s in settings_list:
                print_list.append(s + f': {obj.get(s)}') 
        print("\nImage information: ", print_list)
        print("Cellpose settings: ", self.cellpose_dict)
        print("Trackmate settings: ", self.trackmate_dict, "\n")
        return

    def get_summary_statistics(self):
        """
        Calculate average values of observables for spot, track and edges observables
        """

        spots_exclude_list = ['Frame', 'Z', 'Manual spot color', 'Ellipse center x0', 'Ellipse center y0',\
                              'Shape index', 'Spot ID', 'TRACK_ID']
   
        print("\nSUMMARY STATISTICS FOR SPOTS: ")
        print("All lengths are in phyiscal units, if provided. Otherwise, they are in pixels.")
        print("All times are in physical units, if provided. Otherwise, they are in frames.\n")
        print("Total no. of spots: ", self.Nspots)
        print("Average no. of spots per frame: ", self.Nspots / self.Nframes)
        # Calculate average values of spot observables
        for i, col in enumerate(self.spots_df.columns.drop(spots_exclude_list)):
                avg, std = np.mean(self.spots_df[col]), np.std(self.spots_df[col], ddof = 1)
                print(f"Average value of {col}: {avg:.3f}", " \u00B1", f"{std / self.Nspots:.3f}")

        # Calculate average values of track observables
        if self.tracks_df is not None:
            tracks_exclude_list = ['TRACK_INDEX', 'TRACK_ID','TRACK_START', 'TRACK_STOP', 'TRACK_MAX_SPEED',\
                                    'TRACK_MIN_SPEED', 'TRACK_MEDIAN_SPEED', 'TRACK_STD_SPEED', 'MAX_DISTANCE_TRAVELED',\
                                    'CONFINEMENT_RATIO', 'MEAN_STRAIGHT_LINE_SPEED', 'LINEARITY_OF_FORWARD_PROGRESSION',\
                                        'MEAN_DIRECTIONAL_CHANGE_RATE', 'TRACK_X_LOCATION', 'TRACK_Y_LOCATION',\
                                              'TRACK_Z_LOCATION']

            print("\nSUMMARY STATISTICS FOR TRACKS: ")
            print("All lengths are in phyiscal units, if provided. Otherwise, they are in pixels.")
            print("All times are in physical units, if provided. Otherwise, they are in frames.\n")
            print("Total no. of tracks: ", self.Ntracks)
            print("Average no. of tracks per frame: ", self.Ntracks / self.Nframes)
            # Calculate average values of track observables
            for i, col in enumerate(self.tracks_df.columns.drop(tracks_exclude_list)):
                avg, std = np.mean(self.tracks_df[col]), np.std(self.tracks_df[col], ddof = 1)
                print(f"Average value of {col}: {avg:.3f}", " \u00B1", f"{std / self.Ntracks:.3f}")
        return

    def plot_feature_over_time(self, spot_feature = 'Area'):
        """
        Plots the average values of a feature over time.
        """

        fig, ax = plt.subplots()
        ax.errorbar(self.spots_df.groupby('Frame')['T'].mean(),\
                    self.spots_df.groupby('T')[spot_feature].mean(), \
                    self.spots_df.groupby('T')[spot_feature].std(ddof=1), fmt = 'k.',\
                          capsize = 5, capthick = 2, elinewidth = 2, ms = 5)
        ax.set(xlabel = 'Time', ylabel = spot_feature, title = 'Average' + spot_feature + ' over time')
        plt.show()

        return

    def calculate_grid_statistics(self, Ngrid, include_features = [], return_absolute_cell_counts = False,\
                               save_csv = True, name_path = './grid_statistics'):
        """
        Calculates the mean value of a given feature in each grid square for each frame and returns a dataframe with the results.

        Parameters:
        ----------
        dataframe : pandas dataframe generated by the function 'generate_csv_files'
        Ngrid : int - number of grid squares in the smallest dimension. \
                The number of grid squares in the other dimension is determined by the aspect ratio of the image, 
                with the restriction that the grid squares are square.
        include_features : (list of strings, default = []) - list of features to include in the grid dataframe, 
                            in addition to the standard features number_density, mean_velocity_X and mean_velocity_Y.
                            The possible feature keys are the columns of the spots dataframe generated 
                            by the function 'generate_csv_files'.
        return_absolute_cell_counts : (bool, default = False) - if True, the number of cells in each grid square
                                      is returned instead of the density.
        save_csv : (bool, default=True) - if True, the grid dataframe is saved as a csv file.
        name : (string, default = './grid_statistics') - name of the csv file to be saved. 
                                     It will be saved in the output_folder, if provided, 
                                     otherwise in the image folder

        Returns:
        -------
        grid_df : pandas dataframe - dataframe containing the grid statistics for each frame.
        """

        cols = ['Frame', 'X', 'Y', 'T', 'Velocity_X', 'Velocity_Y']
        add_to_grid = []
        for feature in include_features:
            if feature not in cols:
                cols.append(feature)    
                add_to_grid.append("mean_" + feature.lower())

        # Extract relevant data from dataframe as array
        data = self.spots_df.loc[:, cols].values.astype('float')

        grid_columns = ['Frame', 'T', 'Ngrid','x_center', 'y_center', 'number_density','mean_velocity_X','mean_velocity_Y']
        grid_columns.extend(add_to_grid)

        # Initialize grid dictionary
        self.__initialize_grid(Ngrid)

        # Initialize grid array
        grid_arr = np.ones([self.Nframes * self.__grid_dict['Nsquares'], len(grid_columns)])

        # Loop over all frames
        for i, frame in enumerate(np.arange(self.Nframes)):
            arr_T = data[data[:, 0] == frame]
            time = arr_T[0, 3]
            Ngrid_count = 0
            for y in np.linspace(self.__grid_dict['ymax'] - self.__grid_dict['grid_len'], self.__grid_dict['ymin'], self.__grid_dict['Ny']):
                mask = (arr_T[:, 2] >= y) & (arr_T[:, 2] < y + self.__grid_dict['grid_len'])
                arr_Y = arr_T[mask]
                for x in np.linspace(self.__grid_dict['xmin'], self.__grid_dict['xmax'] - self.__grid_dict['grid_len'], self.__grid_dict['Nx']):
                    mask = (arr_Y[:, 1] >= x) & (arr_Y[:, 1] < x + self.__grid_dict['grid_len'])
            
                    if mask.sum() == 0:
                        grid_arr[frame * self.__grid_dict['Nsquares'] + Ngrid_count, 0:6] = \
                            [frame, time, Ngrid_count, x + self.__grid_dict['grid_len'] / 2, y + self.__grid_dict['grid_len'] / 2, 0]
                        grid_arr[frame * self.__grid_dict['Nsquares'] + Ngrid_count, 6:] = np.nan * np.zeros(len(grid_columns) - 6)
                    else:
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore", category=RuntimeWarning)
                            vx = np.nanmean(arr_Y[mask, 4])
                            vy = np.nanmean(arr_Y[mask, 5])

                        # If true, return the number of cells in each grid as opposed to the density
                        if return_absolute_cell_counts:
                            density = mask.sum() 
                        else:
                            denisty = mask.sum() / (self.__grid_dict['grid_len']**2)     

                        grid_arr[frame * self.__grid_dict['Nsquares'] + Ngrid_count, 0:8] = [frame, time, Ngrid_count, x + self.__grid_dict['grid_len'] / 2, \
                                                                y + self.__grid_dict['grid_len'] / 2, density, vx, vy]
                        # Add additional features to grid (if any)
                        for j, feature in enumerate(add_to_grid):
                            grid_arr[frame * self.__grid_dict['Nsquares'] + Ngrid_count, 8 + j] = np.nanmean(arr_Y[mask, 6 + j])

                    Ngrid_count += 1

        self.grid_df = pd.DataFrame(grid_arr, columns = grid_columns)
        
        if save_csv:
            self.grid_df.to_csv(name_path, sep = ',')

        return self.grid_df

    def visualize_grid_statistics(self, feature = 'number_density', frame_range = [0,0], calculate_average = False, \
                             animate = True, frame_interval = 1200, show = True):
        """
        Visualize the grid statistics (generated by the method calculate_grid_statistics) for a given feature 
        in the form of a heatmap.

        Parameters:
        -----------
        feature : (string, default = 'number_density') - feature to visualize. Must be a column of the grid dataframe \
                  generated by the method calculate_grid_statistics.
        frame_range : (list of ints, default=[0,0]) - range of frames to visualize. Left endpoint is included, right endpoint is not.
                      If [0,0], all frames are visualized.
        calculate_average : (bool, default=False) - if True, the average heatmap over the given frame range 
                            is calculated and visualized.
        animate : (bool, default=True) - if True, the heatmap is animated over the given frame range.
        frame_interval : (int, default=1200) - time between frames in ms (for the animation).
        show : (bool, default=True) - if True, the heatmap is shown.
        """
        if feature not in self.grid_df.columns:
            print("\n Feature not in grid dataframe! Please specify a feature that is in the grid dataframe generated by the method calculate_grid_statistics.\n \
            These features are: \n", self.grid_df.columns, "\n")
        else:
            Nframes = self.Nframes if frame_range == [0,0] else frame_range[1] - frame_range[0]
            frame_range[1] = frame_range[1] if frame_range[1] != 0 else Nframes
            # Set colorbar limits
            vmin, vmax = self.grid_df[feature].min(), self.grid_df[feature].max()

            if self.grid_df is not None:
                data = self.grid_df.loc[:, ['Frame', 'T', 'Ngrid', feature]].values
                data = data[frame_range[0] * self.__grid_dict['Nsquares']:frame_range[1] * self.__grid_dict['Nsquares'],:]
            else: 
                raise OSError("No grid dataframe provided! You must first run the function 'calculate_grid_statistics'.")

            if calculate_average:
                arr_T = data[:,-1].reshape(Nframes, self.__grid_dict['Nsquares'])
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=RuntimeWarning)
                    arr_T = np.nanmean(arr_T, axis = 0)
                title = title=f'{feature.capitalize()} heatmap averaged over frames {frame_range[0]}:{frame_range[1]}'
                self.__heatmap_plotter(0, arr_T, feature, vmin, vmax, title=title)
            else:
                heatmap_plotter_res = lambda i, frame : self.__heatmap_plotter(i, frame, feature, vmin, vmax)
                if animate:
                    self.__animator(data, heatmap_plotter_res, (frame_range[0],frame_range[1]), inter=frame_interval, show=show)
                else:
                    for i in range(frame_range[0], frame_range[1]):
                        fig, ax = plt.subplots()
                        frame = data[data[:, 0] == i, -1]
                        heatmap_plotter_res(i, frame)
            if show:
                plt.show()
        return

    def plot_velocity_field(self, mode = 'field', frame_range = [0,0], calculate_average = False, \
                                animate = True, frame_interval = 1200, show = True):
        """
        Plot or animate the velocity field for a given frame range.

        Parameters:
        -----------
        mode : (string, default = 'field_lines') - mode of visualization. Can be 'field' or 'streamlines'
        frame_range : (list of ints, default=[0,0] - range of frames to visualize. Left endpoint is included, \
                      right endpoint is not. If [0,0], all frames are visualized.
        calculate_average : (bool, default=False) - if True, the average velocity field over the given
                            frame range is calculated and visualized.
        animate : (bool, default=True) - if True, the velocity field is animated over the given frame range.
        frame_interval : (int, default=1200) - time between frames in ms (for the animation).
        show : (bool, default=True) - if True, the velocity field is shown.
    
        """
        if mode not in ['field', 'streamlines']:
            print("\nInvalid mode! Please specify a valid mode: 'field' or 'streamlines'.\n")
            return
        elif mode == 'streamlines':
            plotter = self.__velocity_streamline_plotter
        else:
            plotter = self.__velocity_field_plotter

    
        Nframes = self.Nframes if frame_range == [0,0] else frame_range[1] - frame_range[0]
        frame_range[1] = frame_range[1] if frame_range[1] != 0 else Nframes

        data= self.grid_df.loc[:, ['Frame', 'T', 'x_center', 'y_center', 'mean_velocity_X', 'mean_velocity_Y']].values
        data = data[frame_range[0] * self.__grid_dict['Nsquares']:frame_range[1] * self.__grid_dict['Nsquares'], :]

        x_center = data[:self.__grid_dict['Nsquares'], 2].reshape(self.__grid_dict['Ny'], self.__grid_dict['Nx'])
        y_center = data[:self.__grid_dict['Nsquares'], 3].reshape(self.__grid_dict['Ny'], self.__grid_dict['Nx'])


        if calculate_average:
            arr_vx = data[:, -2].reshape(Nframes, self.__grid_dict['Nsquares'])
            arr_vy = data[:, -1].reshape(Nframes, self.__grid_dict['Nsquares'])
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                arr_vx = np.nanmean(arr_vx, axis = 0).reshape(self.__grid_dict['Ny'], self.__grid_dict['Nx'])
                arr_vy = np.nanmean(arr_vy, axis = 0).reshape(self.__grid_dict['Ny'], self.__grid_dict['Nx'])
            plotter(x_center, y_center, arr_vx, arr_vy, \
                                title=f'Velocity {mode} averaged over frames {frame_range[0]}:{frame_range[1]}')         
        else:  
            if animate:
                anim_wrapper = lambda i, frame, fig, fn: self.__animate_flow_field(i, x_center, y_center, data, fig, plotter,)
                self.__animator(data, plotter, (frame_range[0],frame_range[1]), anim_wrapper, inter=frame_interval, show=show)
            else:
                for i in range(frame_range[0], frame_range[1]):
                    fig, ax = plt.subplots()
                    arr_vx = data[data[:, 0] == i,-2].reshape(self.__grid_dict['Ny'], self.__grid_dict['Nx'])
                    arr_vy = data[data[:, 0] == i, -1].reshape(self.__grid_dict['Ny'], self.__grid_dict['Nx'])
                    plotter(x_center, y_center, arr_vx, arr_vy, i=i)
        if show:
            plt.show()
        return

    def get_density_fluctuations(self, Nwindows = 10, Ndof = 1):
        """
        Calculate defect density fluctuations for different (circular) window sizes (radii). 
        This is done by placing circular windows of a different sizes (= radii) at the center of the image, 
        counting the number of particles within each window, and finally calculating the variance of the 
        number of particles for each window size. The largest window size is determined by the size of the image,
        and the smallest window size is determined by the number of windows.

        Parameters:
        -----------
        Nwindows: (int, default = 10) - number of windows to calculate defect density for.
        Ndof: (int, default = 1) - number of degrees of freedom used to calculate variance

        Returns --> (defect_densities, window_sizes): 
        -------- 
        defect_densities: array of defect densities for different window sizes
        window_sizes: array of window sizes

        """

        # Extract relevant data from dataframe as array
        data = self.spots_df.loc[:, ['Frame', 'X','Y']].values.astype('float')


        # Initialize grid dictionary
        self.__initialize_grid(Ngrid = 8)

        # Intialize array of defect densities
        defect_densities = np.zeros([self.Nframes, Nwindows])

        # Initalize array of average defect densities
        av_defect_densities = np.zeros(self.Nframes)

        # Define center point
        LX = self.__grid_dict['xmax'] - self.__grid_dict['xmin']
        LY = self.__grid_dict['ymax'] - self.__grid_dict['ymin']
        center = np.array([LX/2, LY/2])

        # Calculate the average radius of a spot
        avg_radius = self.spots_df['Radius'].mean()
        
        # Define max. and min. window size
        if self.__grid_dict['Ny'] <= self.__grid_dict['Nx']:
            max_window_size = LY / 2 - 2 * avg_radius
        elif self.__grid_dict['Ny'] > self.__grid_dict['Nx']:
            max_window_size = LX / 2 - 2 * avg_radius

        max_window_size = LX / 2 - 1
        min_window_size = (LX / 2 ) / Nwindows

        # Define window sizes
        window_sizes = np.linspace(min_window_size, max_window_size, Nwindows)

        for frame in np.arange(self.Nframes):
            # Step 1: Convert list of dictionaries to array of defect positions
            defect_positions = data[data[:, 0] == frame, 1:]

            # Step 2: Calculate distance of each defect to center
            distances = np.linalg.norm(defect_positions - center, axis=1)

            # Step 3: Calculate density for each window size
            for i, window_size in enumerate(window_sizes):
                # Get defects within window
                defects_in_window = len(distances[distances < window_size])
                # Calculate  and store density
                defect_densities[frame, i] = defects_in_window / (np.pi * window_size**2)

            # Step 4: Calculate average defect density (using a larger window size than max_window_size)
            defects_in_window = len(distances[distances < max_window_size + avg_radius])
            av_defect_densities[frame] = defects_in_window / (np.pi * (max_window_size + avg_radius)**2)

        # Calculate fluctuations of defect density
        density_fluctuations = 1 / (Nwindows - 1) * np.sum((defect_densities - av_defect_densities[:, np.newaxis])**2)
        return density_fluctuations, window_sizes

    



    ## make it work for one frame
    # make it work for several (avg over more frames --> av of fluctuations over frames
    # make opt N or dens.
    # make opt to average or not?




def main():
    
    model_directory = 'C:\\Users\\Simon Andersen\\miniconda3\\envs\\cellpose\\lib\\site-packages\\cellpose\\models\\cyto_0'
    cellpose_python_filepath = 'C:\\Users\\Simon Andersen\\miniconda3\\envs\\cellpose\\python.exe'
    imj_path = "C:\\Users\\Simon Andersen\\Fiji.app\\ImageJ-win64.exe"

    image_path = "C:\\Users\\Simon Andersen\\Documents\\Uni\\SummerProject\\valeriias mdck data for simon\\24.08.22_698x648\\im0.tif"
    input_directory = "C:\\Users\\Simon Andersen\\Documents\\Uni\\SummerProject\\valeriias mdck data for simon\\24.08.22_698x648"
    image_path = "C:\\Users\\Simon Andersen\\Documents\\Uni\\SummerProject\\16.06.23_stretch_data_698x648\\im0.tif"
    im_p = "C:\\Users\\Simon Andersen\\Documents\\Uni\\SummerProject\\valeriias mdck data for simon\\24.08.22_698x648\\merged.tif"
    show_output = True
    cellpose_dict = {'USE_GPU': True, 'CELL_DIAMETER': 0.0}

    # xml_path, outfolder, use_model = cyto2,nuclei, 
    xml_path = 'C:\\Users\\Simon Andersen\\Projects\\Projects\\CellSegmentationTracker\\resources\\20.09.xml'
    xml_path = "C:\\Users\\Simon Andersen\\Documents\\Uni\\SummerProject\\valeriias mdck data for simon\\24.08.22_698x648\\merged.xml"
    output_directory = "C:\\Users\\Simon Andersen\\Projects\\Projects\\CellSegmentationTracker\\resources"
    
    path = "C:\\Users\\Simon Andersen\\Documents\\Uni\\SummerProject\\NucleiCorrected.tif"
    new_path = path.strip(".tif") + "_resized.tif"
    np = "C:\\Users\\Simon Andersen\\Documents\\Uni\\SummerProject\\merged.tif"
    path_stretch = "C:\\Users\\Simon Andersen\\Documents\\Uni\\SummerProject\\16.06.23_stretch_data_split"
    pn = "C:\\Users\\Simon Andersen\\Documents\\Uni\\SummerProject\\t_164_428 - 2023_03_03_TL_MDCK_2000cells_mm2_10FNh_10min_int_frame1_200_cropped_split"
    pn = "C:\\Users\\Simon Andersen\\Documents\\Uni\\SummerProject\\t_164_428 - 2023_03_03_TL_MDCK_2000cells_mm2_10FNh_10min_int_frame1_200_cropped_split_orig\\im11.tif"
    t1= time.time()
    xml_path = 'C:\\Users\\Simon Andersen\\Projects\\Projects\\CellSegmentationTracker\\resources\\epi500_sample_images.xml'

    dir_path = "C:\\Users\\Simon Andersen\\Projects\\Projects\\CellSegmentationTracker"
    image_path = os.path.join(dir_path, 'resources', 'epi500_sample_images.tif')


    cst = CellSegmentationTracker(imj_path, cellpose_python_filepath, pn, output_folder_path=output_directory, \
                                  show_segmentation=show_output, cellpose_dict=cellpose_dict, use_model='EPI2500',)
    cst.run_segmentation_tracking()
    t2= time.time()
    print("RUNTIME: ", (t2-t1)/60)
    cst.generate_csv_files(save_csv_files=True, name='im11')
   # cst.spots_df = pd.read_csv('./resources/CellSegmentationTracker_spots.csv')

   
    cst.calculate_grid_statistics(Ngrid = 10, include_features=['Area'], return_absolute_cell_counts=True, save_csv=False)

    cst.visualize_grid_statistics(feature = 'number_density', frame_range = [0,1], calculate_average = False, \
                                        animate = False, frame_interval = 800, show = True)

    if 0:

        grid_df = cst.calculate_grid_statistics(Ngrid = 4, include_features=['Area'], return_absolute_cell_counts=True, save_csv=False)
    



        cst.plot_velocity_field(mode = 'streamlines', frame_range = [2,4], calculate_average = False, \
                                    animate = True, frame_interval = 800, show = True)



        grid_df = cst.calculate_grid_statistics(Ngrid = 4, include_features=['Area'], return_absolute_cell_counts=True, save_csv=False)
    



        cst.plot_velocity_field(mode = 'streamlines', frame_range = [2,4], calculate_average = False, \
                                    animate = False, frame_interval = 800, show = False)
        
        cst.plot_velocity_field(mode = 'field', frame_range = [2,4], calculate_average = False, \
                                    animate = False, frame_interval = 800, show = True)

        cst.visualize_grid_statistics(feature = 'dick', frame_range = [0,5], calculate_average = False, \
                                        animate = True, frame_interval = 800, show = True)

    # grid_df = cst.calculate_grid_statistics(Ngrid = 25, return_absolute_cell_counts=True, save_csv=False)

        #cst.plot_feature_over_time('Area')

    if 0:
        cst.visualize_grid_statistics(feature = 'area', frame_range = [1,2], calculate_average = False, \
                                    animate = True, frame_interval = 800, show = True)
        cst.visualize_grid_statistics(feature = 'area', frame_range = [2,2], calculate_average = False, \
                                    animate = True, frame_interval = 800, show = True)

    print(grid_df.info())


    
    print("RUNTIME: ", (t2-t1)/60)

   # cst.generate_csv_files(save_csv_files=False)
    t3 = time.time()
    print("CSV gen time: ", (t3-t2)/60)
    
 #   for col in cst.spots_df.columns:
  #      cst.plot_feature_over_time(col)
    #cst.run_segmentation_tracking()
    
    if 0:
        print(cst.flow_threshold, cst.cellprob_threshold)

        print(cst.spots_df.info()  )
        print(cst.spots_df.describe())
        print(cst.tracks_df.info())
        print(cst.edges_df.info())



        cst.save_csv()
        cst.print_settings()
        print("you made it bro")

if __name__ == '__main__':
    main()
