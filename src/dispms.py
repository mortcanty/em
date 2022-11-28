#!/usr/bin/env python
#******************************************************************************
#  Name:     dispms.py
#  Purpose:  Display a multispectral image
#             allowed formats: uint8, uint16,float32,float64 
#  Usage (from command line):             
#    python dispms.py  [OPTIONS]
#
# Copyright (c) 2018 Mort Canty

import sys, getopt, os, copy
from osgeo import gdal
from osgeo.gdalconst import GA_ReadOnly
import matplotlib.pyplot as plt 
import matplotlib as mpl
import numpy as np

def linstr(x):
    # linear stretch
    return bytestr(x)

def histeqstr(x):
    x = bytestr(x)
    #  histogram equalization stretch
    hist, bin_edges = np.histogram(x, 256, (0, 256))
    cdf = hist.cumsum()
    lut = 255 * cdf / float(cdf[-1])
    return np.interp(x, bin_edges[:-1], lut)

def lin2pcstr(x):
    #  2% linear stretch
    x = bytestr(x)
    hist, bin_edges = np.histogram(x, 256, (0, 256))
    cdf = hist.cumsum()
    lower = 0
    i = 0
    while cdf[i] < 0.02 * cdf[-1]:
        lower += 1
        i += 1
    upper = 255
    i = 255
    while cdf[i] > 0.98 * cdf[-1]:
        upper -= 1
        i -= 1
    fp = (bin_edges - lower) * 255 / (upper - lower)
    fp = np.where(bin_edges <= lower, 0, fp)
    fp = np.where(bin_edges >= upper, 255, fp)
    return np.interp(x, bin_edges, fp)

def bytestr(arr, rng=None):
    #  byte stretch image numpy array
    shp = arr.shape
    arr = arr.ravel()
    if rng is None:
        rng = [np.min(arr), np.max(arr)]
    tmp = (arr - rng[0]) * 255.0 / (rng[1] - rng[0])
    tmp = np.where(tmp < 0, 0, tmp)
    tmp = np.where(tmp > 255, 255, tmp)
    return np.asarray(np.reshape(tmp, shp), np.uint8)

def make_image(redband,greenband,blueband,rows,cols,enhance,rng=None):
    X = np.ones((rows*cols,3),dtype=np.uint8) 
    if enhance == 'linear255':
        i = 0
        for tmp in [redband,greenband,blueband]:
            tmp = tmp.ravel()
            X[:,i] = bytestr(tmp,[0,255])
            i += 1
    elif enhance == 'linear':
        i = 0
        for tmp in [redband,greenband,blueband]:             
            tmp = tmp.ravel()  
            X[:,i] = linstr(tmp)
            i += 1
    elif enhance == 'linear2pc':
        i = 0
        for tmp in [redband,greenband,blueband]:     
            tmp = tmp.ravel()        
            X[:,i] = lin2pcstr(tmp)
            i += 1       
    elif enhance == 'equalization':   
        i = 0
        for tmp in [redband,greenband,blueband]:     
            tmp = tmp.ravel()                
            X[:,i] = histeqstr(tmp)
            i += 1
    elif enhance == 'sqrt':
        i = 0
        for tmp in [redband,greenband,blueband]:     
            tmp = tmp.ravel() 
            tmp = np.sqrt(tmp)            
            mn = np.min(tmp)
            mx = np.max(tmp)
            if mx-mn > 0:
                tmp = (tmp-mn)*255.0/(mx-mn)    
            tmp = np.where(tmp<0,0,tmp)  
            tmp = np.where(tmp>255,255,tmp)
            X[:,i] = lin2pcstr(tmp)
            i += 1
    elif (enhance == 'logarithmic2pc') or (enhance == 'logarithmic'):   
        i = 0
        for tmp in [redband,greenband,blueband]:     
            tmp = tmp.ravel() 
            mn = np.min(tmp)
            if mn < 0:
                tmp = tmp - mn
            idx = np.where(tmp == 0)
            tmp[idx] = np.mean(tmp)  # get rid of black edges
            idx = np.where(tmp > 0)
            tmp[idx] = np.log(tmp[idx])            
            mn = np.min(tmp)
            mx = np.max(tmp)
            if mx-mn > 0:
                tmp = (tmp-mn)*255.0/(mx-mn)    
            tmp = np.where(tmp<0,0,tmp)  
            tmp = np.where(tmp>255,255,tmp)
            if enhance == 'logarithmic2pc':
#              2% linear stretch   
                X[:,i] = lin2pcstr(tmp)
            else:
#              no stretch                
                X[:,i] = tmp       
            i += 1                           
    return np.reshape(X,(rows,cols,3))/255.

def dispms(filename1=None,filename2=None,dims=None,DIMS=None,rgb=None,
           RGB=None,enhance=None,ENHANCE=None,sfn=None,cls=None,CLS=None,
           alpha=None,labels=None):
    gdal.AllRegister()
    if filename1 == None:        
        filename1 = input('Enter image filename: ')
    inDataset1 = gdal.Open(filename1,GA_ReadOnly)    
    try:                   
        cols = inDataset1.RasterXSize    
        rows = inDataset1.RasterYSize  
        bands1 = inDataset1.RasterCount  
    except Exception as e:
        print( 'Error in dispms: %s  --could not read image file'%e )
        return   
    if filename2 is not None:                
        inDataset2 = gdal.Open(filename2,GA_ReadOnly) 
        try:       
            cols2 = inDataset2.RasterXSize    
            rows2 = inDataset2.RasterYSize            
            bands2 = inDataset2.RasterCount       
        except Exception as e:
            print( 'Error in dispms: %s  --could not read second image file'%e )
            return       
    if dims == None:
        dims = [0,0,cols,rows]
    x0,y0,cols,rows = dims
    if rgb == None:
        rgb = [1,1,1]
    r,g,b = rgb
    r = int(np.min([r,bands1]))
    g = int(np.min([g,bands1]))
    b = int(np.min([b,bands1]))
    rng = None
    if enhance == None:
        enhance = 5
    if enhance == 1:
        enhance1 = 'linear255'
    elif enhance == 2:
        enhance1 = 'linear'
    elif enhance == 3:
        enhance1 = 'linear2pc'
    elif enhance == 4:
        enhance1 = 'equalization'
    elif enhance == 5:
        enhance1 = 'logarithmic2pc'   
    elif enhance == 6:
        enhance1 = 'logarithmic'
    elif enhance == 7:
        enhance1 = 'sqrt'
    elif isinstance(enhance,list):
        enhance1 = 'linear'
        rng = enhance   
    else:
        enhance = 'linear2pc' 
    try:  
        if cls is None:
            redband   = np.nan_to_num(inDataset1.GetRasterBand(r).ReadAsArray(x0,y0,cols,rows)) 
            greenband = np.nan_to_num(inDataset1.GetRasterBand(g).ReadAsArray(x0,y0,cols,rows)) 
            blueband  = np.nan_to_num(inDataset1.GetRasterBand(b).ReadAsArray(x0,y0,cols,rows))
        else:
            classimg = inDataset1.GetRasterBand(1).ReadAsArray(x0,y0,cols,rows).ravel()         
            num_classes = np.max(classimg)-np.min(classimg)    
            redband = classimg   
            greenband = classimg
            blueband = classimg
            enhance1 = 'linear'
        inDataset1 = None   
    except  Exception as e:
        print( 'Error in dispms: %s'%e  )
        return
    X1 = make_image(redband,greenband,blueband,rows,cols,enhance1,rng)
    if filename2 is not None:
#      two images 
        if DIMS == None:      
            DIMS = [0,0,cols2,rows2]
        x0,y0,cols,rows = DIMS
        if RGB == None:
            RGB = rgb
        r,g,b = RGB
        r = int(np.min([r,bands2]))
        g = int(np.min([g,bands2]))
        b = int(np.min([b,bands2]))  
        rng = None      
        enhance = ENHANCE
        if enhance == None:              
            enhance = 5
        if enhance == 1:
            enhance2 = 'linear255'
        elif enhance == 2:
            enhance2= 'linear'
        elif enhance == 3:
            enhance2 = 'linear2pc'
        elif enhance == 4:
            enhance2 = 'equalization'
        elif enhance == 5:
            enhance2 = 'logarithmic2pc' 
        elif enhance == 6:
            enhance2 = 'logarithmic'  
        elif enhance == 7:
            enhance2 = 'sqrt' 
        elif isinstance(enhance,list):
            enhance2 = 'linear'
            rng = enhance            
        else:
            enhance = 'linear2pc'          
        try:  
            if CLS is None:
                redband   = np.nan_to_num(inDataset2.GetRasterBand(r).ReadAsArray(x0,y0,cols,rows))
                greenband = np.nan_to_num(inDataset2.GetRasterBand(g).ReadAsArray(x0,y0,cols,rows)) 
                blueband  = np.nan_to_num(inDataset2.GetRasterBand(b).ReadAsArray(x0,y0,cols,rows))
            else:
                classimg = inDataset2.GetRasterBand(1).ReadAsArray(x0,y0,cols,rows).ravel()
                redband = classimg   
                greenband = classimg
                blueband = classimg
                enhance2 = 'linear'
            inDataset2 = None   
        except  Exception as e:
            print( 'Error in dispms: %s'%e )  
            return
        X2 = make_image(redband,greenband,blueband,rows,cols,enhance2,rng)  
        if alpha is not None:
            fig, ax = plt.subplots(figsize=(10,10)) 
            ax.imshow(X2)
            if cls is not None:
                ticks = np.linspace(0.0,1.0,num_classes+1)
                if labels is not None:
                    ticklabels = labels
                else:                    
                    ticklabels = list(map(str,range(0,num_classes+1))) 
                X1[X1 == 0] = np.nan
                cmap = copy.copy(mpl.cm.get_cmap("jet"))
                cmap.set_bad(alpha=0)
                cmap.set_under('black')    
                cax = ax.imshow(X1[:,:,0]-0.01,cmap=cmap,alpha=alpha)  
                cax.set_clim(0.0,1.0)  
                cbar = fig.colorbar(cax,orientation='vertical',  ticks=ticks, shrink=0.8,pad=0.05)
                cbar.set_ticklabels(ticklabels)                            
            else:
                ax.imshow(X1-0.01,alpha=alpha)
 #           ax.set_title('%s: %s: %s: %s\n'%(os.path.basename(filename1),enhance1, str(rgb), str(dims)))            
        else:    
            fig, ax = plt.subplots(1,2,figsize=(20,10))
            if cls:
                cmap = copy.copy(mpl.cm.get_cmap("jet"))
                cmap.set_under('black') 
                cax = ax[0].imshow(X1[:,:,0]-0.01,cmap=cmap)  
                cax.set_clim(0.0,1.0)              
            else:
                ax[0].imshow(X1)             
            ax[0].set_title('%s: %s: %s:  %s\n'%(os.path.basename(filename1),enhance1, str(rgb), str(dims)))           
            if CLS:
                cmap = copy.copy(mpl.cm.get_cmap("jet"))
                cmap.set_under('black')
                cax = ax[1].imshow(X2[:,:,0]-0.01,cmap=cmap)
                cax.set_clim(0.01,1.0)                         
            else:          
                ax[1].imshow(X2)             
            ax[1].set_title('%s: %s: %s:  %s\n'%(os.path.basename(filename2),enhance2, str(RGB), str(DIMS)))
    else:
#      one image
        fig,ax = plt.subplots(figsize=(10,10)) 
        if cls:           
            ticks = np.linspace(0.0,1.0,num_classes+1)
            if labels is not None:
                ticklabels = labels
            else:                    
                ticklabels = list(map(str,range(0,num_classes+1)))  
            cmap = copy.copy(mpl.cm.get_cmap("jet"))
            cmap.set_under('black')
            cax = ax.imshow(X1[:,:,0]-0.01,cmap=cmap)  
            cax.set_clim(0.0,1.0)                          
            cbar = fig.colorbar(cax,orientation='vertical',  ticks=ticks, shrink=0.8,pad=0.05)
            cbar.set_ticklabels(ticklabels)
        else:
            ax.imshow(X1)
        fn = os.path.basename(filename1) 
        if len(fn)>40:
            fn = fn[:37]+' ... '
        ax.set_title('%s: %s: %s: %s\n'%(fn,enhance1, str(rgb), str(dims))) 
    if sfn is not None:
        plt.savefig(sfn,bbox_inches='tight')       
    plt.show()                 

def main():
    usage = '''
Usage: 
--------------------------------------

Display an RGB composite image

python %s [OPTIONS] 

Options:
  -h            this help
  -f  <string>  image filename or left-hand image filename 
                (if not specified, it will be queried)
  -F  <string>  right-hand image filename, if present
  -e  <int>     left enhancement (1=linear255 2=linear 
                3=linear2pc saturation 4=histogram equalization 
                5=logarithmic2ps (default)
                6=logarithmic
                7=square root
     <list>     linear range     
  -E  <int>     right ditto 
  -p  <list>    left RGB band positions e.g. -p [1,2,3]
  -P  <list>    right ditto
  -d  <list>    left spatial subset [x,y,width,height] 
                                  e.g. -d [0,0,200,200]
  -D  <list>    right ditto
  -c            right display as classification image
  -C            left ditto
  -o  <float>   overlay left image onto right with opacity
  -r  <string>  class labels (a string evaluating to a list of strings)
  -s  <string>  save to a file in EPS format      
  
  -------------------------------------'''%sys.argv[0]
  
    options,_ = getopt.getopt(sys.argv[1:],'hco:Cf:F:p:P:d:D:e:E:s:r:')
    filename1 = None
    filename2 = None
    dims = None
    rgb = None
    DIMS = None
    RGB = None
    enhance = None   
    ENHANCE = None
    alpha = None
    cls = None
    CLS = None
    sfn = None
    labels = None
    for option, value in options: 
        if option == '-h':
            print( usage )
            return 
        elif option == '-s':
            sfn = value
        elif option =='-o':
            alpha = eval(value)
        elif option == '-f':
            filename1 = value
        elif option == '-F':
            filename2 = value    
        elif option == '-p':
            rgb = tuple(eval(value))
        elif option == '-P':
            RGB = tuple(eval(value))    
        elif option == '-d':
            dims = eval(value) 
        elif option == '-D':
            DIMS = eval(value)    
        elif option == '-e':
            enhance = eval(value)  
        elif option == '-E':
            ENHANCE = eval(value)    
        elif option == '-c':
            cls = True
        elif option == '-C':
            CLS = True  
        elif option == '-r':
            labels = eval(value)           
                    
    dispms(filename1,filename2,dims,DIMS,rgb,RGB,enhance,ENHANCE,sfn,cls,CLS,alpha,labels)

if __name__ == '__main__':
    main()