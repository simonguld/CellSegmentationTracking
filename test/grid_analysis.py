# Author: Simon Guldager Andersen
# Date (latest update): 

### SETUP ------------------------------------------------------------------------------------

## Imports:
import os
import sys
import time
import warnings
import numpy as np
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats, integrate, interpolate, optimize
from scipy.special import sici, factorial
from iminuit import Minuit
from mpl_toolkits.axes_grid1 import make_axes_locatable
import matplotlib.animation as ani
from matplotlib import rcParams
from cycler import cycler

sys.path.append('..\\Appstat2022\\External_Functions')
from ExternalFunctions import Chi2Regression, BinnedLH, UnbinnedLH
from ExternalFunctions import nice_string_output, add_text_to_ax    # Useful functions to print fit results on figure


## Change directory to current one
dir_path = os.path.dirname(os.path.realpath(__file__))
os.chdir(dir_path)

## Set plotting style and print options
sns.set_theme()
sns.set_style("darkgrid")
sns.set_context("paper") #Possible are paper, notebook, talk and poster

d = {'lines.linewidth': 2, 'axes.titlesize': 18, 'axes.labelsize': 18, 'xtick.labelsize': 12, 'ytick.labelsize': 12,\
     'legend.fontsize': 15, 'font.family': 'serif', 'figure.figsize': (9,6)}
d_colors = {'axes.prop_cycle': cycler(color = ['teal', 'navy', 'coral', 'plum', 'purple', 'olivedrab',\
         'black', 'red', 'cyan', 'yellow', 'khaki','lightblue'])}
rcParams.update(d)
rcParams.update(d_colors)
np.set_printoptions(precision = 5, suppress=1e-10)


### FUNCTIONS ----------------------------------------------------------------------------------

### MAIN ---------------------------------------------------------------------------------------

def calculate_grid_statistics(dataframe, Ngrid, include_features = [], return_absolute_cell_counts = False,\
                               save_csv = True, name_path = './grid_statistics'):
    """
    Calculates the mean value of a given feature in each grid square for each frame and returns a dataframe with the results.

    Parameters:
    ----------
    dataframe : pandas dataframe generated by the function 'generate_csv_files'
    Ngrid : int - number of grid squares in the smallest dimension. The number of grid squares in the other dimension 
            is determined by the aspect ratio of the image, with the restriction that the grid squares are square.
    include_features : list of strings - list of features to include in the grid dataframe, in addition to the standard features
                       number_density, mean_velocity_X and mean_velocity_Y. The possible feature keys are the columns of the 
                       spots dataframe generated by the function 'generate_csv_files'.
    return_absolute_cell_counts : bool - if True, the number of cells in each grid square is returned instead of the density.
    save_csv : bool - if True, the grid dataframe is saved as a csv file.
    name : string - name of the csv file to be saved. It will be saved in the output_folder, if provided, otherwise in the image folder

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
    data = dataframe.loc[:, cols].values

    grid_columns = ['Frame', 'T', 'Ngrid','xmin', 'xmax', 'ymin', 'ymax', 'number_density','mean_velocity_X','mean_velocity_Y']
    grid_columns.extend(add_to_grid)

    # Create empty array to store grid data
    Nframes = int(data[:,0].max() + 1)
    
    xmin, xmax = data[:,1].min(), data[:,1].max()
    ymin, ymax = data[:,2].min(), data[:,2].max()
    Lx, Ly = xmax - xmin, ymax - ymin

    # Calculate number of grid squares in x and y direction
    if Ly < Lx:
        Nygrid = Ngrid
        Nxgrid = int(np.floor(Ngrid * Lx / Ly))     
        grid_len = Ly / Nygrid
        Residual_x = Lx % grid_len
        xmin += Residual_x / 2
        xmax -= Residual_x / 2
    elif Lx < Ly:
        Nxgrid = Ngrid
        Nygrid = int(np.floor(Ngrid * Ly / Lx))
        grid_len = Lx / Nxgrid
        Residual_y = Ly % grid_len
        ymin += Residual_y / 2
        ymax -= Residual_y / 2

    Nsquares = Nxgrid * Nygrid
    dA = grid_len**2

    grid_arr = np.zeros([Nframes * Nsquares, len(grid_columns)])

    # Loop over all frames
    for i, frame in enumerate(np.arange(Nframes)):
        arr_T = data[data[:, 0] == frame]
        time = arr_T[0, 3]
        Ngrid = 0
        
        for x in np.linspace(xmin, xmax - grid_len, Nxgrid):
            mask = (arr_T[:, 1] >= x) & (arr_T[:, 1] < x + grid_len)
            arr_X = arr_T[mask]
      
            for y in np.linspace(ymin, ymax - grid_len, Nygrid):
                mask = (arr_X[:, 2] >= y) & (arr_X[:, 2] < y + grid_len)
                # If no spots in grid, set all values(except for density) to nan
                if mask.sum() == 0:
                    grid_arr[frame * Nsquares + Ngrid, 0:8] = [frame, time, Ngrid, x, x + grid_len, y, y + grid_len, 0]
                    grid_arr[frame * Nsquares + Ngrid, 8:] = np.nan * np.zeros(len(grid_columns) - 8)
                else:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", category=RuntimeWarning)
                        vx = np.nanmean(arr_X[mask, 4])
                        vy = np.nanmean(arr_X[mask, 5])

                    # If true, return the number of cells in each grid as opposed to the density
                    if return_absolute_cell_counts:
                        density = mask.sum() 
                    else:
                        denisty = mask.sum() / dA      

                    grid_arr[frame * Nsquares + Ngrid, 0:10] = [frame, time, Ngrid, x, x + grid_len, y, y + grid_len, density, vx, vy]

                    # Add additional features to grid (if any)
                    for j, feature in enumerate(add_to_grid):
                        grid_arr[frame * Nsquares + Ngrid, 10 + j] = np.nanmean(arr_X[mask, 6 + j])

                Ngrid += 1

    grid_df = pd.DataFrame(grid_arr, columns = grid_columns)

    if save_csv:
        grid_df.to_csv(name_path, sep = ',')

    return grid_df


# step 2: get it to work for multiple frames
# step 3: get it to work for vector fields

def visualize_grid_statistics(grid_dataframe, feature = 'number_density', frame_range = [0,0], calculate_average = False, \
                              save_fig = False, name = 'grid_statistics', show = True):
    

    grid_columns = ['Frame', 'T', 'Ngrid','xmin', 'xmax', 'ymin', 'ymax', 'number_density','mean_velocity_X','mean_velocity_Y']

    xmin, xmax = grid_dataframe['xmin'].min(), grid_dataframe['xmax'].max()
    ymin, ymax = grid_dataframe['ymin'].min(), grid_dataframe['ymax'].max()
    vmin, vmax = grid_dataframe[feature].min(), grid_dataframe[feature].max()
    Nsquares = int(np.round(grid_dataframe['Ngrid'].max()) + 1)
    Nframes = int(np.round(grid_dataframe['Frame'].max() + 1)) if frame_range == [0,0] else frame_range[1] - frame_range[0]
    frame_range[1] = frame_range[1] if frame_range[1] != 0 else Nframes

    Lx, Ly = xmax - xmin, ymax - ymin
    grid_len = grid_dataframe['xmax'].loc[0] - grid_dataframe['xmin'].loc[0]

    # Calculate number of grid squares in x and y direction
    if Ly < Lx:
        Nygrid = int(np.round(Ly / grid_len))
        Nxgrid = int(np.round(Nsquares / Nygrid) )
    elif Lx <= Ly:
        Nxgrid = int(np.round(Lx / grid_len))
        Nygrid = int(np.round(Nsquares / Nxgrid) )

    data = grid_dataframe.loc[:, ['Frame', 'T', 'Ngrid', feature]].values

    if calculate_average:
        arr_T = data[frame_range[0] * Nsquares:frame_range[1] * Nsquares,-1].reshape(Nframes, Nsquares)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            arr_T = np.nanmean(arr_T, axis = 0)
        title = title=f'{feature.capitalize()} heatmap averaged over frames {frame_range[0]}:{frame_range[1]}'
        plotter(0, arr_T, Nxgrid, Nygrid, xmin, xmax, ymin, ymax, grid_len, feature, vmin, vmax,\
                 title=title)


    #plotter_res = lambda i, frame : plotter(i, frame, Nxgrid, Nygrid, xmin, xmax, ymin, ymax, grid_len, feature, vmin, vmax)
    #animate(data, plotter_res, (0,Nframes), inter=800, show=show)

    if 0:
        arr_T = data[data[:, 0] == 0][:, -1]

        

        # reshape to grid
        arr_grid = np.flip(arr_T.reshape(Nxgrid, Nygrid).T, axis = 0)

        # plot
        fig, ax = plt.subplots()
        xticklabels = np.round(np.linspace(xmin + Lx/10, xmax - Lx/10, 4), 2) 
        yticklabels = np.round(np.linspace(ymax + Ly/10, ymin - Ly/10, 4), 2)
        sns.heatmap(arr_grid, cmap = 'viridis'), #xticklabels=xticklabels,\
                    # yticklabels=yticklabels,)
        ax.set(xlabel = 'x', ylabel = 'y', title = f'{feature.capitalize()} heatmap')
        ax.set_xticks(ticks = np.linspace(0.5,Nxgrid-0.5,4), labels=xticklabels)
        ax.set_yticks(ticks = np.linspace(0.5,Nygrid-0.5,4), labels=yticklabels)

    if show:
        plt.show()
    return

def plotter(i, frame, Nxgrid, Nygrid, xmin, xmax, ymin, ymax, grid_len, feature, vmin, vmax, title=None):
    """
    Plots a heatmap of the given feature for a given frame.
    """

    # reshape to grid
    arr_grid = np.flip(frame.reshape(Nxgrid, Nygrid).T, axis = 0)
    Lx, Ly = xmax - xmin, ymax - ymin

    xticklabels = np.round(np.linspace(xmin + Lx / 10, xmax - Lx / 10, 4), 2) 
    yticklabels = np.round(np.linspace(ymax + Ly / 10, ymin - Ly / 10, 4), 2)

    ax = sns.heatmap(arr_grid, cmap = 'viridis', vmin=vmin, vmax=vmax)

    title = f'{feature.capitalize()} heatmap for frame = {i}' if title is None else title
    ax.set(xlabel = 'x', ylabel = 'y', title = title)
    ax.set_xticks(ticks = np.linspace(0.5,Nxgrid-0.5,4), labels=xticklabels)
    ax.set_yticks(ticks = np.linspace(0.5,Nygrid-0.5,4), labels=yticklabels)
    return

def animate(arr, fn, rng, inter=200, show=True):
    """Show a frame-by-frame animation.

    Parameters:
    arr -- the data array
    fn -- the plot function (argument: fram number, frame)
    rng -- range of the frames to be plotted
    interval -- time between frames (ms)
    """

    # create the figure
    fig = plt.figure()

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

    anim = ani.FuncAnimation(fig, animate_fn,
                             frames=np.arange(rng[0], rng[1]),
                             interval=inter, blit=False)
    if show==True:
      plt.show()
      return

    return anim


def main():
    df = pd.read_csv('../resources/epi500_sample_images_spots.csv')
        
    grid_df = calculate_grid_statistics(df, Ngrid = 15, return_absolute_cell_counts=True, include_features=['Area','Circularity'], save_csv = False,)
    
    grid_columns = ['Frame', 'T', 'Ngrid','xmin', 'xmax', 'ymin', 'ymax', 'number_density','mean_velocity_X','mean_velocity_Y']

    visualize_grid_statistics(grid_df, feature = 'mean_area', calculate_average = True, \
                              save_fig = False, name = 'grid_statistics', show = True)

    if 0:

        xmin, xmax = grid_df['xmin'].min(), grid_df['xmax'].max()
        ymin, ymax = grid_df['ymin'].min(), grid_df['ymax'].max()
        Nsquares = grid_df['Ngrid'].max() + 1

        feature = 'number_density'
        Lx, Ly = xmax - xmin, ymax - ymin
        grid_len = grid_df['xmax'].loc[0] - grid_df['xmin'].loc[0]

        # Calculate number of grid squares in x and y direction
        if Ly < Lx:
            Nygrid = int(np.round(Ly / grid_len))
            Nxgrid = int(np.round(Nsquares / Nygrid) )
        elif Lx <= Ly:
            Nxgrid = int(np.round(Lx / grid_len))
            Nygrid = int(np.round(Nsquares / Nxgrid) )
    
        print(Nxgrid, Nygrid, Nsquares, int(Ly / grid_len), Lx / grid_len)

        vmin = grid_df[feature].min()
        vmax = grid_df[feature].max()

        def plotter(i, frame):

            # reshape to grid
            arr_grid = np.flip(frame.reshape(Nxgrid, Nygrid).T, axis = 0)

            xticklabels = np.round(np.linspace(xmin, xmax, Nxgrid) + grid_len / 2, 2) 
            yticklabels = np.round(np.linspace(ymax, ymin, Nygrid) + grid_len / 2, 2)
            ax = sns.heatmap(arr_grid, cmap = 'viridis', xticklabels=xticklabels,\
                            yticklabels=yticklabels, vmin=vmin, vmax=vmax)
            ax.set(xlabel = 'x', ylabel = 'y', title = f'{feature.capitalize()} heatmap for frame = {i}')

        animate(grid_df.loc[:, ['T', 'Ngrid', feature]].values, plotter, (0,1), inter=800, show=True)


    # x_ticks = np.round(np.linspace(xmin, xmax, Nxgrid),2)
        #y_ticks = np.round(np.linspace(ymin, ymax, Nygrid),2)

        #ax.set_xticks(ticks = np.arange(Nxgrid),labels=x_ticks)
        #ax.set_yticks(ticks = np.arange(Nygrid), labels=y_ticks)
  
        plt.show()

        
        print(arr_grid)
        print(arr_grid.shape)
        print(arr_grid.sum())


    if 0:
 
        Nframes = int(data[:,0].max() + 1)
        #Nframes = data

        xmin, xmax = data[:,1].min(), data[:,1].max()
        ymin, ymax = data[:,2].min(), data[:,2].max()

        Lx = xmax - xmin
        Ly = ymax - ymin

        Nygrid = 50

        dy = Ly / Nygrid
        dA = dy**2

        Residual_x = Lx % dy
        Nxgrid = int(np.floor(Lx / dy))
        Nsquares = Nxgrid * Nygrid

        xmin += Residual_x / 2
        xmax -= Residual_x / 2
        Lx = xmax - xmin


    
        columns = ['Frame','Ngrid','xmin', 'xmax', 'ymin', 'ymax', 'density','grid_VELOCITY_X','grid_VELOCITY_Y']
        grid_arr = np.zeros([Nframes * Nsquares, len(columns)])

        ### HANDLE NANS!!!

        t1 = time.time()
        for i, frame in enumerate(np.arange(Nframes)):
            arr_T = data[data[:, 0] == frame]
            Ngrid = 0
            
            for j, x in enumerate(np.linspace(xmin, xmax - dy, Nxgrid)):
                mask = (arr_T[:, 1] >= x) & (arr_T[:, 1] < x + dy)
                arr_X = arr_T[mask]
        
                for k, y in enumerate(np.linspace(ymin, ymax - dy, Nygrid)):
                    mask = (arr_X[:, 2] >= y) & (arr_X[:, 2] < y + dy)

                    density = mask.sum()  / dA
                    vx = np.nanmean(arr_X[mask, 3])
                    vy = np.nanmean(arr_X[mask, 4])

                    grid_arr[frame * Nsquares + Ngrid] = [frame, Ngrid, x, x + dy, y, y + dy, density, vx, vy]
                    Ngrid += 1

        t2 = time.time()
        print(f'Time elapsed: {t2 - t1:.2f} s')
        
            
        print(grid_arr[:20])
        print(grid_arr.shape)
        print(grid_arr[-20:]    )
        grid_df = pd.DataFrame(grid_arr, columns = columns)

        print(grid_df.info())
        print(grid_df.head())
        print(grid_df.describe())
        
    

if __name__ == '__main__':
    main()




"""
for j, x in enumerate(np.linspace(xmin, xmax, Nxgrid - 1)):
            interval = pd.IntervalIndex([pd.Interval(x, x + dy, closed='both')])
            mask = df_T['X'].apply(lambda x: x in interval)
            df_X = df_T.loc[mask]
            for k, y in enumerate(np.linspace(ymin, ymax, Nygrid - 1)):
                
                interval = pd.IntervalIndex([pd.Interval(y, y + dy, closed='both')])
                mask = df_X['Y'].apply(lambda x: x in interval)
                df_XY = df_X.loc[mask]
                Nspots = len(df_XY.index)
                density = Nspots / dA
                vx = x + dy / 2
                vy = y + dy / 2
                grid_df.loc[j*Nygrid + k] = [frame, Nspots, x, x + dy, y, y + dy, density, vx, vy]


           
"""





