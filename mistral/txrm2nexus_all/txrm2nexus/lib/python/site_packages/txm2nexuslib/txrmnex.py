#!/usr/bin/python

from OleFileIO_PL import *   
import numpy as np
import h5py 
import nxs
import sys
import struct
import datetime
import time
import argparse
import re


# Questions for NeXus:

# What is the distance? self.nxinstrument['sample']['distance']= is explained in the definition: distance between sample and detector
# (1'float': it could be the distance between the sample and the detector. 
# Look if I cand find it inside the .txrm). ((self.nxinstrument['sample']['distance']='float'))

# Control monitor. What is exactly that? What we should do? We put 1s for the moment.

# PositionsX, Y, Z. What is exactly that? From where these distances has to be measured?

# Float images will never be accepted in Nexus? It would be nice for scientists.

# We don't have any dark-field. Dark-field is mandatory?

# FlatField corresponds to the BrightField? Let's say yes. Dividing every pixel by the FF pixel.


# Questions solved by Xradia:
# Where is the sample name? SampleID. ####
# Ask for orientation of the axis X, Y, Z. Distance to CCD to ZonePlate and from ZonePlate to Sample. Explained in the word. ####



class txrmNXtomo:


    #filename_output_hdf5='uo.hdf5',
    def __init__(self, files, files_order='s', zero_deg_in=None, zero_deg_final=None,
                 title='X-ray tomography', sourcename='ALBA', sourcetype='Synchrotron X-ray Source', 
                 sourceprobe='x-ray', instrument='BL09 @ ALBA', sample='Unknown'):


        self.exitprogram=0
        if (len(files)<2):
            print('At least one input file and one output file must be specified.\n')
            self.exitprogram=1
            return


        self.files=files
        self.filename_hdf5 = files[-1]        
        self.num_input_files = len(files)-1 #number of files minus the output file.
        self.orderlist = list(files_order)
        self.num_input_files_verify = len(self.orderlist) #number of input files.

        if(self.num_input_files != self.num_input_files_verify):
            print('Number of input files must be equal to number of characters of files_order.')
            print('Do not forget to give an output file at the end of the list of input files.\n')
            self.exitprogram=1
            return
                   
        if 's' not in files_order:
            print('Tomography data file (txrm) has to be specified, inicate it as \'s\' in the argument option -o.\n')
            self.exitprogram=1
            return

        index_tomography_file = files_order.index('s')
        self.filename_txrm = files[index_tomography_file]

        self.filename_zerodeg_in = zero_deg_in
        self.filename_zerodeg_final = zero_deg_final

        self.numrows = 0
        self.numcols = 0
        self.nSampleFrames = 0      
        self.monitorcounts = 0
        self.count_num_sequence = 0
      
        self.brightexists=0
        self.darkexists=0
        for i in range (0, self.num_input_files):
            #Create bright field structure    
            if(self.orderlist[i] == 'b'):
                self.brightexists=1
                self.numrows_bright = 0
                self.numcols_bright = 0
                self.datatype_bright = 'uint16'      

                            
            #Create dark field structure    
            if(self.orderlist[i] == 'd'):
                self.darkexists = 1
                self.numrows_dark = 0
                self.numcols_dark = 0
                self.datatype_dark ='uint16' 


        """ The attribute self.metadata indicates if the metadata has been 
        # extracted or not. If metadata has not been extracted from the 'txrm' 
        file, we cannot extract the data from the images in the 'txrm'. """
        self.metadata=0
     
        self.title = title
        self.sourcename = sourcename
        self.sourcetype = sourcetype
        self.sourceprobe = sourceprobe
        self.instrumentname = instrument
        self.samplename = sample
        self.datatype = 'uint16' #two bytes
        
        self.nFramesSampleTotal = 0
        self.nFramesBrightTotal = 0
        self.nFramesDarkTotal = 0
        self.monitorsize = (self.nFramesSampleTotal + self.nFramesBrightTotal + self.nFramesDarkTotal) 

        self.num_sample_sequence = []
        self.num_bright_sequence = []
        self.num_dark_sequence = []    

        self.datatype_zerodeg = 'uint16'
        self.numrows_zerodeg = 0
        self.numcols_zerodeg = 0

        self.programname = 'txrm2nexus.py'
        self.nxentry = 0
        self.nxsample = 0
        self.nxmonitor = 0
        self.nxinstrument = 0
        self.nxdata = 0
        self.nxdetectorsample = 0

        self.pixelsize=1
        self.CCDdetector_pixelsize = 13
        self.CCDdetector_pixelsize_string = '13 um' #in micrometers
        self.magnification = 1

        self.sample_distance_enc = 0
        self.detector_distance_enc = 0
        self.zoneplate_distance_enc = 0
        self.sample_detector_distance = 0
        self.sample_zonplate_zeroenc = 0
        self.sample_detector_zeroenc = 0
        return



 
    def NXtomo_structure(self):    
        #create_basic_structure
    
        self.nxentry = nxs.NXentry(name= "NXtomo")
           
        self.nxentry['title']=self.filename_txrm
        self.nxentry['definition'] = 'NXtomo'
        
        self.nxsample = nxs.NXsample()
        self.nxentry.insert(self.nxsample)
        self.nxsample['name'] = self.samplename

        self.nxmonitor = nxs.NXmonitor(name= 'control')
        self.nxentry.insert(self.nxmonitor)

        self.nxdata = nxs.NXdata()
        self.nxentry.insert(self.nxdata)

        self.nxinstrument = nxs.NXinstrument(name= 'instrument')
        self.nxinstrument['name'] = self.instrumentname        
        self.nxinstrument['name'].attrs['CCD pixel size'] = self.CCDdetector_pixelsize_string
        self.nxentry.insert(self.nxinstrument)

        self.nxsource = nxs.NXsource(name = 'source')
        self.nxinstrument.insert(self.nxsource)
        self.nxinstrument['source']['name'] = self.sourcename
        self.nxinstrument['source']['type'] = self.sourcetype
        self.nxinstrument['source']['probe'] = self.sourceprobe

        self.nxdetectorsample = nxs.NXdetector(name = 'sample')
        self.nxinstrument.insert(self.nxdetectorsample)  

        self.nxentry.save(self.filename_hdf5, 'w5')

        return 

 
    #### Function used to convert the metadata from .txrm to NeXus .hdf5
    def convert_metadata(self):

        verbose = False
        print("Trying to convert txrm metadata to NeXus HDF5.")
        
        #Opening the .txrm files as Ole structures
        ole = OleFileIO(self.filename_txrm)
        #txrm files have been opened
        
        self.nxentry['program_name'] = self.programname
        self.nxentry['program_name'].attrs['version']='1.0'
        self.nxentry['program_name'].attrs['configuration'] = (self.programname + ' ' 
                                                              + ' '.join(sys.argv[1:]))###########Perque aixo abans sortia i ara no surt?
        self.nxentry['program_name'].write()

        # Sample-ID
        if ole.exists('SampleInfo/SampleID'):   
            stream = ole.openstream('SampleInfo/SampleID')
            data = stream.read()
            struct_fmt ='<'+'50s' 
            samplename = struct.unpack(struct_fmt, data)
            if self.samplename != 'Unknown':
                self.samplename = samplename[0]    
            if verbose: 
                print "SampleInfo/SampleID: %s " % self.samplename 
            self.nxsample['name'] = nxs.NXfield(
                name='name', value=self.samplename)    
            self.nxsample['name'].write()    
        else:
            print("There is no information about SampleID")


        # Detector to Sample distance
        if ole.exists('PositionInfo/AxisNames'):   
            stream = ole.openstream('PositionInfo/AxisNames')
            data = stream.read()
            lendatabytes=len(data)
            formatstring='<'+str(lendatabytes)+'c'
            struct_fmt = formatstring
            axis_names_raw = struct.unpack(struct_fmt, data)
            axis_names_raw = ''.join(axis_names_raw)
            axis_names_raw = axis_names_raw.replace("\x00", " ")
            axis_names=re.split('\s+\s+', axis_names_raw)
            sample_enc_z_string=axis_names[2]
            detector_enc_z_string=axis_names[23]
            current_name=axis_names[28]            

        if ole.exists('ConfigureBackup/ConfigCamera/Camera 1/ConfigZonePlates/DetZero'):   
            stream = ole.openstream('ConfigureBackup/ConfigCamera/Camera 1/ConfigZonePlates/DetZero')
            data = stream.read()
            struct_fmt = '<1f'
            sample_to_detector_zero_enc = struct.unpack(struct_fmt, data)
            self.sample_detector_zeroenc = sample_to_detector_zero_enc[0]

        if ole.exists('PositionInfo/MotorPositions'):   
            stream = ole.openstream('PositionInfo/MotorPositions')
            data = stream.read(112)
            struct_fmt = '<28f'
            axis = struct.unpack(struct_fmt, data)
            self.sample_distance_enc = axis[2] #this is already in um
            self.detector_distance_enc = axis[23]*1000 #from mm to um
        if (sample_enc_z_string == "Sample Z" and detector_enc_z_string == "Detector Z"):
            self.sample_detector_distance = self.sample_detector_zeroenc + self.detector_distance_enc + self.sample_distance_enc
            self.nxinstrument['sample']['distance'] = nxs.NXfield(
                name='x_pixel_size', value=self.sample_detector_distance, attrs = {'units': 'um'}) 
            self.nxinstrument['sample']['distance'].write()  
        else:     
            print("Microscope motor names have changed. Maybe motors have been added or deleted.")
            print("Distances between detector and sample, and positions will NOT be correctly calculated")
         

        # Pixel-size
        if ole.exists('ImageInfo/PixelSize'):   
            stream = ole.openstream('ImageInfo/PixelSize')
            data = stream.read()
            struct_fmt = '<1f'
            pixelsize = struct.unpack(struct_fmt, data)
            self.pixelsize = pixelsize[0]
            if verbose: 
                print "ImageInfo/PixelSize: %f " %  pixelsize  
            self.nxinstrument['sample']['x_pixel_size'] = nxs.NXfield(
                name='x_pixel_size', value=self.pixelsize, attrs = {'units': 'um'})
            self.nxinstrument['sample']['x_pixel_size'].write()    
            self.nxinstrument['sample']['y_pixel_size'] = nxs.NXfield(
                name='y_pixel_size', value=self.pixelsize, attrs = {'units': 'um'}) 
            self.nxinstrument['sample']['y_pixel_size'].write()    
        else:
            print("There is no information about PixelSize")

        #Magnification
        # X-Ray Magnification
        if ole.exists('ImageInfo/XrayMagnification'):   
            stream = ole.openstream('ImageInfo/XrayMagnification')
            data = stream.read(4)
            struct_fmt = '<1f'
            XrayMagnification = struct.unpack(struct_fmt, data)
            self.magnification = XrayMagnification[0]
            if verbose: 
                print "ImageInfo/XrayMagnification: %f " %  XrayMagnification  
            self.nxinstrument['sample']['magnification'] = nxs.NXfield(
                    name = 'magnification', value=self.magnification)
            self.nxinstrument['sample']['magnification'].write()



    
	    # Tomography data size 
        if (ole.exists('ImageInfo/NoOfImages') and 
            ole.exists('ImageInfo/ImageWidth') and 
            ole.exists('ImageInfo/ImageHeight')):                  
                    
            stream = ole.openstream('ImageInfo/NoOfImages')
            data = stream.read()
            nimages = struct.unpack('<I', data)
            if verbose: 
                print "ImageInfo/NoOfImages = %i" % nimages[0] 
            self.nSampleFrames = np.int(nimages[0])
        
            stream = ole.openstream('ImageInfo/ImageHeight')
            data = stream.read()
            ximage = struct.unpack('<I', data)    
            if verbose: 
                print "ImageInfo/ImageHeight = %i" % ximage[0]  
            self.numrows = np.int(ximage[0])
            
            stream = ole.openstream('ImageInfo/ImageWidth')
            data = stream.read()
            yimage = struct.unpack('<I', data)
            if verbose: 
                print "ImageInfo/ImageWidth = %i" % yimage[0]  
            self.numcols = np.int(yimage[0])

        else:
            print('There is no information about the tomography size (ImageHeight,'
            'ImageWidth or Number of images)')


        # Accelerator current for each image (machine current)
        if (current_name == "machine_current"):
            if ole.exists('PositionInfo/MotorPositions'):   
                stream = ole.openstream('PositionInfo/MotorPositions')
                number_of_floats= 30*self.nSampleFrames
                struct_fmt = '<'+str(number_of_floats)+'f'
                number_of_bytes = number_of_floats * 4 #4 bytes every float
                data = stream.read(number_of_bytes)
                axis = struct.unpack(struct_fmt, data)

                currents = self.nSampleFrames*[0]
                for i in range(self.nSampleFrames):
                    currents[i] = axis[30*i+28] #In mA  
                self.nxinstrument['sample']['current'] = nxs.NXfield(
                    name = 'current', value=currents, attrs = {'units': 'mA'})
                self.nxinstrument['sample']['current'].write()  
        else:     
            print("Microscope motor names have changed. Index 28 does not correspond to machine_current.")


        # Energy            	
        if ole.exists('ImageInfo/Energy'):
            stream = ole.openstream('ImageInfo/Energy')
    	    data = stream.read()
     	    struct_fmt = "<{0:10}f".format(self.nSampleFrames)
       	    try: #we found some txrm images (flatfields) with different encoding of data
                energies = struct.unpack(struct_fmt, data)
            except struct.error:
                print >> sys.stderr, 'Unexpected data length (%i bytes). Trying to unpack energies with: "f"+"36xf"*(nSampleFrames-1)'%len(data) 
                struct_fmt = '<'+"f"+"36xf"*(self.nSampleFrames-1)
                energies = struct.unpack(struct_fmt, data)
            if verbose: print "ImageInfo/Energy: \n ",  energies  
            self.nxinstrument['source']['energy'] = nxs.NXfield(
                name='energy', value = energies, attrs = {'units': 'eV'}) 
            self.nxinstrument['source']['energy'].write()
        else:
            print('There is no information about the energies with which '  
                   'have been taken the different tomography images')


        # Exposure Times            	
        if ole.exists('ImageInfo/ExpTimes'):
            stream = ole.openstream('ImageInfo/ExpTimes')
            data = stream.read()
            struct_fmt = "<{0:10}f".format(self.nSampleFrames)
            try: #we found some txrm images (flatfields) with different encoding of data
                exptimes = struct.unpack(struct_fmt, data)
            except struct.error:
                print >> sys.stderr, 'Unexpected data length (%i bytes). Trying to unpack exposure times with: "f"+"36xf"*(nSampleFrames-1)'%len(data) 
                struct_fmt = '<'+"f"+"36xf"*(self.nSampleFrames-1)
                exptimes = struct.unpack(struct_fmt, data)
            if verbose: print "ImageInfo/ExpTimes: \n ",  exptimes  
            self.nxinstrument['sample']['ExpTimes'] = nxs.NXfield(
                name='ExpTimes', value = exptimes, attrs = {'units': 's'}) 
            self.nxinstrument['sample']['ExpTimes'].write()
        else:
            print('There is no information about the exposure times with which '  
                   'have been taken the different tomography images')


        # DataType: 10 float; 5 uint16 (unsigned 16-bit (2-byte) integers)
        if ole.exists('ImageInfo/DataType'):                  
            stream = ole.openstream('ImageInfo/DataType')
            data = stream.read()
            struct_fmt = '<1I'
            datatype = struct.unpack(struct_fmt, data)
            datatype = int(datatype[0])
            if datatype == 5:
                self.datatype = 'uint16'
            else:
                self.datatype = 'float'
            if verbose: 
                print "ImageInfo/DataType: %s " %  self.datatype      
        else:
            print("There is no information about DataType")

        # Start and End Times 
        if ole.exists('ImageInfo/Date'):  
            stream = ole.openstream('ImageInfo/Date')       
            data = stream.read()
            dates = struct.unpack('<'+'17s23x'*self.nSampleFrames, data) 
            
            startdate = dates[0]
            [day, hour] = startdate.split(" ")
            [month, day, year] = day.split("/")
            [hour, minute, second] = hour.split(":")    
            
            year = '20'+year
            year = int(year)   
            month = int(month)
            day = int(day)
            hour = int(hour)
            minute = int(minute)
            second = int(second)

            starttime = datetime.datetime(year, month, day, 
                                          hour, minute, second)                 
            starttimeiso = starttime.isoformat()
            times = time.mktime(starttime.timetuple())

            if verbose: 
                print "ImageInfo/Date = %s" % starttimeiso 
            self.nxentry['start_time'] = str(starttimeiso)
            self.nxentry['start_time'].write()    

            enddate = dates[self.nSampleFrames-1]    
            [endday, endhour] = enddate.split(" ")
            [endmonth, endday, endyear] = endday.split("/")
            [endhour, endminute, endsecond] = endhour.split(":")

            endyear = '20'+endyear
            endyear = int(endyear)   
            endmonth = int(endmonth)
            endday = int(endday)
            endhour = int(endhour)
            endminute = int(endminute)
            endsecond = int(endsecond)

            endtime = datetime.datetime(endyear, endmonth, endday, 
                                        endhour, endminute, endsecond)                 
            endtimeiso = endtime.isoformat()
            endtimes = time.mktime(endtime.timetuple())   
            
            if verbose: 
                print "ImageInfo/Date = %s" % endtimeiso 
            self.nxentry['end_time'] = str(endtimeiso)
            self.nxentry['end_time'].write()

        else:
            print("There is no information about Date")

        # Sample rotation angles 
        if ole.exists('ImageInfo/Angles'):    
            stream = ole.openstream('ImageInfo/Angles')
            data = stream.read()
            struct_fmt = '<{0:10}f'.format(self.nSampleFrames)
            angles = struct.unpack(struct_fmt, data)
            if verbose: 
                print "ImageInfo/Angles: \n ",  angles
            self.nxsample['rotation_angle'] = nxs.NXfield(
                name='rotation_angle', value=angles, attrs={'units': 'degrees'})
            self.nxsample['rotation_angle'].write() 
            self.nxdata['rotation_angle'] = nxs.NXlink(
                target=self.nxsample['rotation_angle'], group=self.nxdata)
            self.nxdata['rotation_angle'].write()

        else:
            print('There is no information about the angles at' 
                   'which have been taken the different tomography images')

        # Sample translations in X, Y and Z 
        # X sample translation: nxsample['z_translation']
        if ole.exists('ImageInfo/XPosition'):

            stream = ole.openstream('ImageInfo/XPosition')
            data = stream.read()
            struct_fmt = "<{0:10}f".format(self.nSampleFrames)
            try: #we found some txrm images (flatfields) with different encoding of data #
                xpositions = struct.unpack(struct_fmt, data) 
            except struct.error:
                print >> sys.stderr, 'Unexpected data length (%i bytes). Trying to unpack XPositions with: "f"+"36xf"*(nSampleFrames-1)'%len(data) 
                struct_fmt = '<'+"f"+"36xf"*(self.nSampleFrames-1)
                xpositions = struct.unpack(struct_fmt, data)
            if verbose: 
                print "ImageInfo/XPosition: \n ",  xpositions  

            self.nxsample['x_translation'] = nxs.NXfield(
                name='x_translation', value=xpositions, attrs={'units': 'um'})   
            self.nxsample['x_translation'].write()

        else:
            print("There is no information about xpositions")

        # Y sample translation: nxsample['z_translation']
        if ole.exists('ImageInfo/YPosition'):

            stream = ole.openstream('ImageInfo/YPosition')
            data = stream.read()
            struct_fmt = "<{0:10}f".format(self.nSampleFrames)
            try: #we found some txrm images (flatfields) with different encoding of data.
                ypositions = struct.unpack(struct_fmt, data) 
            except struct.error:
                print >> sys.stderr, 'Unexpected data length (%i bytes). Trying to unpack YPositions with: "f"+"36xf"*(nSampleFrames-1)'%len(data) 
                struct_fmt = '<'+"f"+"36xf"*(self.nSampleFrames-1)
                ypositions = struct.unpack(struct_fmt, data)
            if verbose: 
                print "ImageInfo/YPosition: \n ",  ypositions  
      
            self.nxsample['y_translation'] = nxs.NXfield(
                name='y_translation', value=ypositions, attrs={'units': 'um'})   
            self.nxsample['y_translation'].write()

        else:
            print("There is no information about xpositions")

        # Z sample translation: nxsample['z_translation']
        if ole.exists('ImageInfo/ZPosition'):
    
            stream = ole.openstream('ImageInfo/ZPosition')
            data = stream.read()
            struct_fmt = "<{0:10}f".format(self.nSampleFrames)
            try: #we found some txrm images (flatfields) with different encoding of data.
                zpositions = struct.unpack(struct_fmt, data)
            except struct.error:
                print >> sys.stderr, 'Unexpected data length (%i bytes). Trying to unpack ZPositions with: "f"+"36xf"*(nSampleFrames-1)'%len(data)
                struct_fmt = '<'+"f"+"36xf"*(self.nSampleFrames-1)
                zpositions = struct.unpack(struct_fmt, data)
            if verbose: 
                print "ImageInfo/ZPosition: \n ",  zpositions  
      
            self.nxsample['z_translation'] = nxs.NXfield(
                name='z_translation', value=zpositions, attrs={'units': 'um'})   
            self.nxsample['z_translation'].write()

        else:
            print("There is no information about xpositions")

        
        self.metadata=1

        ole.close()
        print ("Meta-Data conversion from 'txrm' to NeXus HDF5 has been done.\n")  
        return


    def convert_zero_deg_images(self, ole_zerodeg):
        verbose=False

        # DataType: 10 float; 5 uint16 (unsigned 16-bit (2-byte) integers)
        if ole_zerodeg.exists('ImageInfo/DataType'):                  
            stream = ole_zerodeg.openstream('ImageInfo/DataType')
            data = stream.read()
            struct_fmt = '<1I'
            datatype_zerodeg = struct.unpack(struct_fmt, data)
            datatype_zerodeg = int(datatype_zerodeg[0])
            if datatype_zerodeg == 5:
                self.datatype_zerodeg='uint16'
            else:
                self.datatype_zerodeg= 'float'
            if verbose: 
                print "ImageInfo/DataType: %s " %  self.datatype_zerodeg     
        else:
            print("There is no information about DataType")


        # Zero degrees data size 
        if (ole_zerodeg.exists('ImageInfo/NoOfImages') and 
            ole_zerodeg.exists('ImageInfo/ImageWidth') and 
            ole_zerodeg.exists('ImageInfo/ImageHeight')):                  
                          
            stream = ole_zerodeg.openstream('ImageInfo/ImageHeight')
            data = stream.read()
            yimage = struct.unpack('<I', data)     
            self.numrows_zerodeg = np.int(yimage[0])
            if verbose: 
                print "ImageInfo/ImageHeight = %i" % yimage[0]
            stream = ole_zerodeg.openstream('ImageInfo/ImageWidth')
            data = stream.read()
            ximage = struct.unpack('<I', data)
            self.numcols_zerodeg = np.int(ximage[0])
            if verbose: 
                print "ImageInfo/ImageWidth = %i" % ximage[0]  
        else:
            print('There is no information about the 0 degrees image size (ImageHeight,'
            ' or about ImageWidth)')


        if ole_zerodeg.exists('ImageData1/Image1'):        
            img_string = "ImageData1/Image1"
            stream = ole_zerodeg.openstream(img_string) 
            data = stream.read()
            if self.datatype == 'uint16':
                struct_fmt = "<{0:10}H".format(self.numrows_zerodeg*self.numcols_zerodeg)
                imgdata = struct.unpack(struct_fmt, data)
            elif self.datatype == 'float':                   
                struct_fmt = "<{0:10}f".format(self.numrows_zerodeg*self.numcols_zerodeg)
                imgdata = struct.unpack(struct_fmt, data)
            else:                            
                print "Wrong data type"

            imgdata_zerodeg = np.flipud(np.reshape(imgdata, (self.numrows, self.numcols), order='A'))
        else:
            imgdata_zerodeg = 0
        return imgdata_zerodeg


    #### Read single image. Function that will only be used inside 
    #### convert_tomography() for converting the full tomography thanks to multiple slabs.   
    def extract_single_image(self, ole, numimage): 

        #Read the images - They are stored in the txrm as ImageData1, ImageData2... 
        #Each folder contains 100 images 1-100, 101-200... 
        img_string = "ImageData%i/Image%i" % (np.ceil(numimage/100.0), numimage)
        stream = ole.openstream(img_string)
        data = stream.read()
    
        if self.datatype == 'uint16':
            struct_fmt = "<{0:10}H".format(self.numrows*self.numcols)
            imgdata = struct.unpack(struct_fmt, data)
        elif self.datatype == 'float':                   
            struct_fmt = "<{0:10}f".format(self.numrows*self.numcols)
            imgdata = struct.unpack(struct_fmt, data)
        else:                            
            print "Wrong data type"
            return
            
        singleimage = np.flipud(np.reshape(imgdata, (self.numrows, self.numcols), order='A'))
        singleimage = np.reshape(singleimage, (1, self.numrows, self.numcols), order='A')
        #singleimage = np.reshape(imgdata, (1, self.numrows, self.numcols), order='A')
        return singleimage


    #### Read single image. Function that will only be used inside 
    #### convert_tomography() for converting the full tomography thanks to multiple slabs.   
    def extract_single_image_bright(self, ole, numimage): 

        #Read the images - They are stored in the txrm as ImageData1, ImageData2... 
        #Each folder contains 100 images 1-100, 101-200... 
        img_string = "ImageData%i/Image%i" % (np.ceil(numimage/100.0), numimage)
        stream = ole.openstream(img_string)
        data = stream.read()
    
        if self.datatype_bright == 'uint16':
            struct_fmt = "<{0:10}H".format(self.numrows_bright*self.numcols_bright)
            imgdata = struct.unpack(struct_fmt, data)
        elif self.datatype_bright == 'float':                   
            struct_fmt = "<{0:10}f".format(self.numrows_bright*self.numcols_bright)
            imgdata = struct.unpack(struct_fmt, data)
        else:                            
            print "Wrong data type"
            return
            
        singleimage = np.flipud(np.reshape(imgdata, (self.numrows_bright, self.numcols_bright), order='A'))
        singleimage = np.reshape(singleimage, (1, self.numrows_bright, self.numcols_bright), order='A')
        #singleimage = np.reshape(imgdata, (1, self.numrows_bright, self.numcols_bright), order='A')
        return singleimage


    #### Read single image. Function that will only be used inside 
    #### convert_tomography() for converting the full tomography thanks to multiple slabs.   
    def extract_single_image_dark(self, ole, numimage): 

        #Read the images - They are stored in the txrm as ImageData1, ImageData2... 
        #Each folder contains 100 images 1-100, 101-200... 
        img_string = "ImageData%i/Image%i" % (np.ceil(numimage/100.0), numimage)
        stream = ole.openstream(img_string)
        data = stream.read()
    
        if self.datatype_dark == 'uint16':
            struct_fmt = "<{0:10}H".format(self.numrows_dark*self.numcols_dark)
            imgdata = struct.unpack(struct_fmt, data)
        elif self.datatype_dark == 'float':                   
            struct_fmt = "<{0:10}f".format(self.numrows_dark*self.numcols_dark)
            imgdata = struct.unpack(struct_fmt, data)
        else:                            
            print "Wrong data type"
            return
             
        singleimage = np.flipud(np.reshape(imgdata, (self.numrows_dark, self.numcols_dark), order='A'))
        singleimage = np.reshape(singleimage, (1, self.numrows_dark, self.numcols_dark), order='A')
        #singleimage = np.reshape(imgdata, (1, self.numrows_dark, self.numcols_dark), order='A')
        return singleimage




    #### Function used to convert all the tomography images (main data), from .txrm to NeXus .hdf5.
    def convert_tomography(self):    
        
        verbose=False

        if self.metadata == 1:
                
            if (self.filename_zerodeg_in != None):
                ole_zerodeg_in = OleFileIO(self.filename_zerodeg_in)        
                image_zerodeg_in = self.convert_zero_deg_images(ole_zerodeg_in)
                self.nxinstrument['sample']['0_degrees_initial_image'] = nxs.NXfield(
                    name='0_degrees_initial_image', value=image_zerodeg_in, dtype=self.datatype_zerodeg) 
                self.nxinstrument['sample']['0_degrees_initial_image'].attrs['Data Type']=self.datatype_zerodeg 
                self.nxinstrument['sample']['0_degrees_initial_image'].attrs['Image Height']=self.numrows_zerodeg
                self.nxinstrument['sample']['0_degrees_initial_image'].attrs['Image Width']=self.numcols_zerodeg
                self.nxinstrument['sample']['0_degrees_initial_image'].write()
                print('Zero degrees initial image converted')	

            if (self.filename_zerodeg_final != None):
                ole_zerodeg_final = OleFileIO(self.filename_zerodeg_final)
                image_zerodeg_final = self.convert_zero_deg_images(ole_zerodeg_final)
                self.nxinstrument['sample']['0_degrees_final_image'] = nxs.NXfield(
                    name='0_degrees_final_image', value=image_zerodeg_final , dtype=self.datatype_zerodeg)
                self.nxinstrument['sample']['0_degrees_final_image'].attrs['Data Type']=self.datatype_zerodeg 
                self.nxinstrument['sample']['0_degrees_final_image'].attrs['Image Height']=self.numrows_zerodeg
                self.nxinstrument['sample']['0_degrees_final_image'].attrs['Image Width']=self.numcols_zerodeg
                self.nxinstrument['sample']['0_degrees_final_image'].write()
                print('Zero degrees final image converted')        


            print("\nConverting tomography image data from txrm to NeXus HDF5.")
            #Opening the .txrm files as Ole structures
            ole = OleFileIO(self.filename_txrm)


            #Bright-Field
            if not self.brightexists:
                print('\nWarning: Bright-Field is not present, the generated HDF5 file will not be compliant with the NeXus standard. \n')      
         

            count_brightfield_file = 0
            count_darkfield_file = 0
            counter_bright_frames = 0
            counter_dark_frames = 0
            for i in range(0, len(self.orderlist)):
                print(self.orderlist)

                ole = OleFileIO(self.files[i])


                #Tomography Data Images
                if self.orderlist[i] == 's':
                    
                    #self.nxinstrument['sample']['data']=NXfield_comp(name='data', dtype=self.datatype , shape=[nxs.UNLIMITED, self.numrows, self.numcols], nxslab_dims=[1,self.numrows,self.numcols] )
                    if (self.datatype == 'float'):
                        self.nxinstrument['sample']['data'] = nxs.NXfield(
                            name='data', dtype='float32' , shape=[nxs.UNLIMITED, self.numrows, self.numcols])
                    else:
                        self.nxinstrument['sample']['data'] = nxs.NXfield(
                            name='data', dtype=self.datatype , shape=[nxs.UNLIMITED, self.numrows, self.numcols])

                    self.nxinstrument['sample']['data'].attrs['Data Type']=self.datatype 
                    self.nxinstrument['sample']['data'].attrs['Number of Frames']=self.nSampleFrames
                    self.nxinstrument['sample']['data'].attrs['Image Height']=self.numrows
                    self.nxinstrument['sample']['data'].attrs['Image Width']=self.numcols
                    self.nxinstrument['sample']['data'].write()

                    
                    for numimage in range(0, self.nSampleFrames):
                        print('Image %i converted' % (numimage+1))
                        self.count_num_sequence = self.count_num_sequence+1
                        tomoimagesingle = self.extract_single_image(ole, numimage+1) 
                        
                        self.num_sample_sequence.append(self.count_num_sequence)

                        slab_offset = [numimage, 0, 0]
                        self.nxinstrument['sample']['data'].put(tomoimagesingle, slab_offset, refresh=False)
                        self.nxinstrument['sample']['data'].write()

                    self.nxdata['data'] = nxs.NXlink(target=self.nxinstrument['sample']['data'], group=self.nxdata)
                    self.nxdata['data'].write()
                    ole.close()
		    print('\n Image pixels are {0}rows * {1}columns \n'.format(self.numrows, self.numcols))	

                #Bright-Field
                elif self.orderlist[i] == 'b':                
                    count_brightfield_file = count_brightfield_file+1
                    
                    # DataType_bright: 10 float; 5 uint16 (unsigned 16-bit (2-byte) integers)
                    if ole.exists('ImageInfo/DataType'):                  
                        stream = ole.openstream('ImageInfo/DataType')
                        data = stream.read()
                        struct_fmt = '<1I'
                        datatype_bright = struct.unpack(struct_fmt, data)
                        datatype_bright = int(datatype_bright[0])
                        if datatype_bright == 5:
                            self.datatype_bright = 'uint16'
                        else:
                            self.datatype_bright = 'float'
                        if verbose: 
                            print "ImageInfo/DataType: %s " %  self.datatype_bright     
                    else:
                        print("There is no information about BrightField DataType")


                    # Tomography data size 
                    if (ole.exists('ImageInfo/NoOfImages') and 
                        ole.exists('ImageInfo/ImageWidth') and 
                        ole.exists('ImageInfo/ImageHeight')):                  
                                
                        stream = ole.openstream('ImageInfo/NoOfImages')
                        data = stream.read()
                        nimages = struct.unpack('<I', data)
                        if verbose: 
                            print "ImageInfo/NoOfImages = %i" % nimages[0] 
                        nBrightFrames = np.int(nimages[0])
                    
                        if count_brightfield_file == 1:
                            stream = ole.openstream('ImageInfo/ImageHeight')
                            data = stream.read()
                            ximage = struct.unpack('<I', data)    
                            if verbose: 
                                print "ImageInfo/ImageHeight = %i" % ximage[0]  
                            self.numrows_bright = np.int(ximage[0])
                            
                            stream = ole.openstream('ImageInfo/ImageWidth')
                            data = stream.read()
                            yimage = struct.unpack('<I', data)
                            if verbose: 
                                print "ImageInfo/ImageWidth = %i" % yimage[0]  
                            self.numcols_bright = np.int(yimage[0])

                    else:
                        print('There is no information about the tomography size (ImageHeight,'
                        'ImageWidth or Number of images)')

                    if count_brightfield_file == 1:
                        
                        self.nxbright = nxs.NXgroup(name= 'bright_field')
                        self.nxinstrument.insert(self.nxbright)
                        self.nxbright.write() 
                        self.nxinstrument['bright_field']['data'] = nxs.NXfield(
                            name = 'data', dtype = self.datatype_bright , shape = [nxs.UNLIMITED, self.numrows_bright, self.numcols_bright]) 

                        self.nxinstrument['bright_field']['data'].attrs['Data Type'] = self.datatype_bright 
                        self.nxinstrument['bright_field']['data'].attrs['Image Height'] = self.numrows_bright
                        self.nxinstrument['bright_field']['data'].attrs['Image Width'] = self.numcols_bright
                        self.nxinstrument['bright_field']['data'].write()


                    for numimage in range(0, nBrightFrames):
                        print ('Bright-Field image %i converted' % (numimage+1))
                        self.count_num_sequence = self.count_num_sequence+1
                        tomoimagebright = self.extract_single_image_bright(ole, numimage+1)
                    
                        self.num_bright_sequence.append(self.count_num_sequence)
                        slab_offset = [counter_bright_frames, 0, 0]
                        self.nxinstrument['bright_field']['data'].put(tomoimagebright, slab_offset, refresh=False)
                        self.nxinstrument['bright_field']['data'].write()
                        counter_bright_frames = counter_bright_frames+1
                        


                    ################################################
                    # machine_current name of FF images
                    if ole.exists('PositionInfo/AxisNames'):   
                        stream = ole.openstream('PositionInfo/AxisNames')
                        data = stream.read()
                        lendatabytes=len(data)
                        formatstring='<'+str(lendatabytes)+'c'
                        struct_fmt = formatstring
                        axis_names_raw = struct.unpack(struct_fmt, data)
                        axis_names_raw = ''.join(axis_names_raw)
                        axis_names_raw = axis_names_raw.replace("\x00", " ")
                        axis_names = re.split('\s+\s+', axis_names_raw)
                        current_name_FF = axis_names[28]   
	                
	                
	                # Accelerator current for each image of FF (machine current)
                    if (current_name_FF == "machine_current"):
                        if ole.exists('PositionInfo/MotorPositions'):   
                            stream = ole.openstream('PositionInfo/MotorPositions')
                            number_of_floats= 30*nBrightFrames
                            struct_fmt = '<'+str(number_of_floats)+'f'
                            number_of_bytes = number_of_floats * 4 #4 bytes every float
                            data = stream.read(number_of_bytes)
                            axis = struct.unpack(struct_fmt, data)

                            currents_FF = nBrightFrames*[0]
                            for i in range(nBrightFrames):
                                currents_FF[i] = axis[30*i+28] #In mA  
                            self.nxinstrument['bright_field']['current'] = nxs.NXfield(
                                name = 'current', value=currents_FF, attrs = {'units': 'mA'})
                            self.nxinstrument['bright_field']['current'].write()
                        else:
                            print('PositionInfo/MotorPositions does not exist in txrm FF tree')  
                    else:     
                        print("Microscope motor names have changed. Index 28 does not correspond to machine_current.")
	                ###########################################            



                    # Exposure Times            	
                    if ole.exists('ImageInfo/ExpTimes'):
                        stream = ole.openstream('ImageInfo/ExpTimes')
                        data = stream.read()
                        struct_fmt = "<{0:10}f".format(nBrightFrames)
                        try: #we found some txrm images (flatfields) with different encoding of data
                            exptimes = struct.unpack(struct_fmt, data)
                        except struct.error:
                            print >> sys.stderr, 'Unexpected data length (%i bytes). Trying to unpack exposure times with: "f"+"36xf"*(nBrightFrames-1)'%len(data) 
                            struct_fmt = '<'+"f"+"36xf"*(nBrightFrames-1)
                            exptimes = struct.unpack(struct_fmt, data)
                        if verbose: print "ImageInfo/ExpTimes: \n ",  exptimes  
                        self.nxinstrument['bright_field']['ExpTimes'] = nxs.NXfield(
                            name='ExpTimes', value = exptimes, attrs = {'units': 's'}) 
                        self.nxinstrument['bright_field']['ExpTimes'].write()
                    else:
                        print('There is no information about the exposure times with which '  
                               'have been taken the different tomography images')
   
                    ole.close()
                    print('\n BrightField pixels are {0}rows * {1}columns \n'.format(self.numrows_bright, self.numcols_bright))

                #Post-Dark-Field
                elif self.orderlist[i] == 'd':
                    count_darkfield_file = count_darkfield_file+1
						
                    # DataType_dark: 10 float; 5 uint16 (unsigned 16-bit (2-byte) integers)
                    if ole.exists('ImageInfo/DataType'):                  
                        stream = ole.openstream('ImageInfo/DataType')
                        data = stream.read()
                        struct_fmt = '<1I'
                        datatype_dark = struct.unpack(struct_fmt, data)
                        datatype_dark = int(datatype_dark[0])
                        if datatype_dark == 5:
                            self.datatype_dark = 'uint16'
                        else:
                            self.datatype_dark = 'float'
                        if verbose: 
                            print "ImageInfo/DataType: %s " %  self.datatype_dark     
                    else:
                        print("There is no information about DarkField DataType")


                    # Tomography data size 
                    if (ole.exists('ImageInfo/NoOfImages') and 
                        ole.exists('ImageInfo/ImageWidth') and 
                        ole.exists('ImageInfo/ImageHeight')):                  
                                
                        stream = ole.openstream('ImageInfo/NoOfImages')
                        data = stream.read()
                        nimages = struct.unpack('<I', data)
                        if verbose: 
                            print "ImageInfo/NoOfImages = %i" % nimages[0] 
                        nDarkFrames = np.int(nimages[0])
                    
                        if count_darkfield_file == 1:
                            stream = ole.openstream('ImageInfo/ImageHeight')
                            data = stream.read()
                            ximage = struct.unpack('<I', data)    
                            if verbose: 
                                print "ImageInfo/ImageHeight = %i" % ximage[0]  
                            self.numrows_dark = np.int(ximage[0])
                            
                            stream = ole.openstream('ImageInfo/ImageWidth')
                            data = stream.read()
                            yimage = struct.unpack('<I', data)
                            if verbose: 
                                print "ImageInfo/ImageWidth = %i" % yimage[0]  
                            self.numcols_dark = np.int(yimage[0])

                    else:
                        print('There is no information about the tomography size (ImageHeight,'
                        'ImageWidth or Number of images)')


                    if count_darkfield_file == 1:
                        self.nxdark = nxs.NXgroup(name= 'dark_field')
                        self.nxinstrument.insert(self.nxdark)
                        self.nxdark.write() 
                        self.nxinstrument['dark_field']['data'] = nxs.NXfield(
                            name = 'data', dtype = self.datatype_dark , shape = [nxs.UNLIMITED, self.numrows_dark, self.numcols_dark]) 

                        self.nxinstrument['dark_field']['data'].attrs['Data Type'] = self.datatype_dark 
                        self.nxinstrument['dark_field']['data'].attrs['Image Height'] = self.numrows_dark
                        self.nxinstrument['dark_field']['data'].attrs['Image Width'] = self.numcols_dark
                        self.nxinstrument['dark_field']['data'].write()


                    for numimage in range(0, nDarkFrames):
                        print ('Dark-Field image %i converted' % (numimage+1))
                        self.count_num_sequence = self.count_num_sequence+1
                        tomoimagedark = self.extract_single_image_dark(ole, numimage+1)

                        self.num_dark_sequence.append(self.count_num_sequence)
                        slab_offset = [counter_dark_frames, 0, 0]
                        self.nxinstrument['dark_field']['data'].put(tomoimagedark, slab_offset, refresh=False)
                        self.nxinstrument['dark_field']['data'].write()
                        counter_dark_frames = counter_dark_frames+1


                    ################################################
                    # machine_current name of DF images
                    if ole.exists('PositionInfo/AxisNames'):   
                        stream = ole.openstream('PositionInfo/AxisNames')
                        data = stream.read()
                        lendatabytes=len(data)
                        formatstring='<'+str(lendatabytes)+'c'
                        struct_fmt = formatstring
                        axis_names_raw = struct.unpack(struct_fmt, data)
                        axis_names_raw = ''.join(axis_names_raw)
                        axis_names_raw = axis_names_raw.replace("\x00", " ")
                        axis_names = re.split('\s+\s+', axis_names_raw)
                        current_name_DF = axis_names[28]   
	                
	                
	                # Accelerator current for each image of DF (machine current)
                    if (current_name_DF == "machine_current"):
                        if ole.exists('PositionInfo/MotorPositions'):   
                            stream = ole.openstream('PositionInfo/MotorPositions')
                            number_of_floats= 30*nDarkFrames
                            struct_fmt = '<'+str(number_of_floats)+'f'
                            number_of_bytes = number_of_floats * 4 #4 bytes every float
                            data = stream.read(number_of_bytes)
                            axis = struct.unpack(struct_fmt, data)

                            currents_DF = nDarkFrames*[0]
                            for i in range(nDarkFrames):
                                currents_DF[i] = axis[30*i+28] #In mA  
                            self.nxinstrument['dark_field']['current'] = nxs.NXfield(
                                name = 'current', value=currents_DF, attrs = {'units': 'mA'})
                            self.nxinstrument['dark_field']['current'].write()
                        else:
                            print('PositionInfo/MotorPositions does not exist in txrm DarkField tree')  
                    else:     
                        print("Microscope motor names have changed. Index 28 does not correspond to machine_current.")
	                ###########################################  
	                
    
	                # Exposure Times            	
                    if ole.exists('ImageInfo/ExpTimes'):
                        stream = ole.openstream('ImageInfo/ExpTimes')
                        data = stream.read()
                        struct_fmt = "<{0:10}f".format(nDarkFrames)
                        try: #we found some txrm images (flatfields) with different encoding of data
                            exptimes = struct.unpack(struct_fmt, data)
                        except struct.error:
                            print >> sys.stderr, 'Unexpected data length (%i bytes). Trying to unpack exposure times with: "f"+"36xf"*(nDarkFrames-1)'%len(data) 
                            struct_fmt = '<'+"f"+"36xf"*(nDarkFrames-1)
                            exptimes = struct.unpack(struct_fmt, data)
                        if verbose: print "ImageInfo/ExpTimes: \n ",  exptimes  
                        self.nxinstrument['dark_field']['ExpTimes'] = nxs.NXfield(
                            name='ExpTimes', value = exptimes, attrs = {'units': 's'}) 
                        self.nxinstrument['dark_fieldd']['ExpTimes'].write()
                    else:
                        print('There is no information about the exposure times with which '  
                               'have been taken the different tomography images')
                                                                  
                    ole.close()
		    print('\n DarkField pixels are {0}rows * {1}columns \n'.format(self.numrows_dark, self.numcols_dark))	

            self.nxinstrument['sample']['sequence_number'] = self.num_sample_sequence         
            self.nxinstrument['sample']['sequence_number'].write()

            if(self.brightexists):
                self.nxinstrument['bright_field']['sequence_number'] = self.num_bright_sequence         
                self.nxinstrument['bright_field']['sequence_number'].write()

            if(self.darkexists):
                self.nxinstrument['dark_field']['sequence_number'] = self.num_dark_sequence         
                self.nxinstrument['dark_field']['sequence_number'].write()

            self.nFramesSampleTotal = len(self.num_sample_sequence)
            self.nFramesBrightTotal = len(self.num_bright_sequence)
            self.nFramesDarkTotal = len(self.num_dark_sequence)

            # NXMonitor data: Not used in TXM microscope. 
            # Used to normalize in function fo the beam intensity (to verify). 
            # In the ALBA-BL09 case all the values will be set to 1.
            self.monitorsize = (self.nFramesSampleTotal + self.nFramesBrightTotal + self.nFramesDarkTotal)
            self.monitorcounts = np.ones((self.monitorsize), dtype= np.uint16)
            self.nxmonitor['data'] = nxs.NXfield(
                name='data', value=self.monitorcounts)
            self.nxmonitor['data'].write()

        else:
            print('Metadata had not been extracted; thus, the tomography image data cannot be extracted.')
            print('Function convert_metadata() has to be called before calling convert_tomography().')
    
        return

















"""from nxs import NXfield #needs Nexus v>=4.3
from nxs import napi, NeXusError
import numpy

class NXfield_comp(NXfield):
    
    #NOTE: THE CONSTRUCTOR IS OPTIONAL. IF NOT IMPLEMENTED, WE CAN STILL USE THE nxslab_dims PROPERTY
    def __init__(self, value=None, name='field', dtype=None, shape=(), group=None,
                 attrs={}, nxslab_dims=None, **attr):
        NXfield.__init__(self, value=value, name=name, dtype=dtype, shape=shape, group=group,
                 attrs=attrs, **attr)
        self._slab_dims = nxslab_dims
        
    def write(self):
        
        #Write the NXfield, including attributes, to the NeXus file.
        
        if self.nxfile:
            if self.nxfile.mode == napi.ACC_READ:
                raise NeXusError("NeXus file is readonly")
            if not self.infile:
                shape = self.shape
                if shape == (): shape = (1,)
                with self.nxgroup as path:
                    if self.nxslab_dims is not None:
                    #compress
                        path.compmakedata(self.nxname, self.dtype, shape, 'lzw', 
                                          self.nxslab_dims)
                    else:
                    # Don't use compression
                        path.makedata(self.nxname, self.dtype, shape)
                self._infile = True
            if not self.saved:            
                with self as path:
                    path._writeattrs(self.attrs)
                    value = self.nxdata
                    if value is not None:
                        path.putdata(value)
                self._saved = True
        else:
            raise IOError("Data is not attached to a file")
    
    def _getnxslabdims(self):
        try:
            return self._nxslab_dims
        except:
            slab_dims = None
        #even if slab_dims have not been set, check if the dataset is large 
        shape = self.shape or (1,)
        if numpy.prod(shape) > 10000:
            slab_dims = numpy.ones(len(shape),'i')
            slab_dims[-1] = min(shape[-1], 100000)
        return slab_dims
    
    def _setnxslabdims(self, slab_dims):
        self._nxslab_dims = slab_dims
    
    nxslab_dims = property(_getnxslabdims,_setnxslabdims,doc="Slab (a.k.a. chunk) dimensions for compression")
    """


    
    




