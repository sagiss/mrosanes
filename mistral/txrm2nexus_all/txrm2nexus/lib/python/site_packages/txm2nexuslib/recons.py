#!/usr/bin/python


import numpy as np
import nxs
import sys
import struct
import os


class recons_normalize:


    def __init__(self, inputfile, avgtomnorm):

        self.avgtomnorm = avgtomnorm
        self.filename_nexus = inputfile        
        self.input_nexusfile=nxs.open(self.filename_nexus, 'r')

        self.tomonorm = nxs.NXentry(name= "TomoNormalized")
               
        self.nxdata = nxs.NXdata(name = 'ratios')
        self.tomonorm.insert(self.nxdata) 
        
        self.outputfilehdf5 = inputfile.split('.')[0]+'_norm'+'.hdf5'
        self.tomonorm.save(self.outputfilehdf5, 'w5')

        # Ratios for the exposure times
        self.ratios_exptimes = list()
        
        # Ratios for the currents.
        self.ratios_currents_tomo = list()
        self.ratios_currents_brightfield = list()  
           
        # Note: brightfield= FlatField= FF   
        self.exposuretimes_brightfield = 0
        self.averagebrightfield_exptimes = 0
        self.currents_brightfield = 0
        self.data_brightfield = 0
        self.nFramesFF = 0
        self.numrowsFF = 0
        self.numcolsFF = 0

        self.exposuretimes_tomo = 0
        self.currents_tomo = 0
        self.data_tomo = 0
        self.nFramesSample = 0                
        self.numrows = 0
        self.numcols = 0
        
        self.averagebright = 0
        self.normalizedtomo_singleimage = 0
        self.normalizedTomoStack = 0

        self.boolean_current_exists = 0
        return

 

    def normalize_tomo(self):


        self.input_nexusfile.opengroup('NXtomo')
        self.input_nexusfile.opengroup('instrument')
        self.input_nexusfile.opengroup('sample')
        
        
        try: 
            self.input_nexusfile.opendata('current')
            self.currents = self.input_nexusfile.getdata()
            self.currenttwo = self.currents[2]
            self.boolean_current_exists = 1
            self.input_nexusfile.closedata()  
        except:
            self.boolean_current_exists = 0
            try:
                self.input_nexusfile.closedata()
            except:
                pass
            
        if (self.boolean_current_exists == 1):
            
            print('\nInformation about currents is present in hdf5 file')
        
            self.input_nexusfile.opendata('data')
            infoshape = self.input_nexusfile.getinfo()
            dimensions_singleimage_tomo = (infoshape[0][1], infoshape[0][2])
            self.nFramesSample = infoshape[0][0]
            self.numrows = infoshape[0][1]
            self.numcols = infoshape[0][2]
            self.input_nexusfile.closedata()
        
            self.input_nexusfile.opendata('ExpTimes')
            self.exposuretimes_tomo = self.input_nexusfile.getdata()
            self.input_nexusfile.closedata()
            
            self.input_nexusfile.opendata('current')
            self.currents_tomo = self.input_nexusfile.getdata()
            self.input_nexusfile.closedata()
            self.input_nexusfile.closegroup()


            self.input_nexusfile.opengroup('bright_field')
            self.input_nexusfile.opendata('data')
            self.data_brightfield = self.input_nexusfile.getdata()
            self.input_nexusfile.closedata()
            
            self.input_nexusfile.opendata('ExpTimes')
            self.exposuretimes_brightfield = self.input_nexusfile.getdata()
            self.input_nexusfile.closedata()
            
            self.input_nexusfile.opendata('current')
            self.currents_brightfield = self.input_nexusfile.getdata()
            self.input_nexusfile.closedata()
            self.input_nexusfile.closegroup()

            # Average of the FF exposure times.
            for i in range(len(self.exposuretimes_brightfield)):
                self.averagebrightfield_exptimes = self.averagebrightfield_exptimes + self.exposuretimes_brightfield[i]     
            self.averagebrightfield_exptimes = self.averagebrightfield_exptimes / len(self.exposuretimes_brightfield)

            print('\nBrightField Exposure Time is {0}\n'.format(self.averagebrightfield_exptimes))
            
            num_exptimes_tomo = len(self.exposuretimes_tomo)       
            self.ratios_exptimes = [None]*num_exptimes_tomo
            
            num_currents_tomo = len(self.currents_tomo) 
            self.ratios_currents_tomo = [None]*num_currents_tomo
            
            num_currents_brightfield = len(self.currents_brightfield) 
            self.ratios_currents_brightfield = [None]*num_currents_brightfield

            dimensions_singleimage_brightfield = self.data_brightfield[0].shape      
            
            
            
            self.tomonorm['ExpTimesTomo'] = self.exposuretimes_tomo
            self.tomonorm['ExpTimesTomo'].write()
            self.tomonorm['Avg_FF_ExpTime'] = self.averagebrightfield_exptimes
            self.tomonorm['Avg_FF_ExpTime'].write()
            self.tomonorm['CurrentsTomo'] = self.currents_tomo
            self.tomonorm['CurrentsTomo'].write()
            self.tomonorm['CurrentsFF'] = self.currents_brightfield
            self.tomonorm['CurrentsFF'].write()
            
            
            if (dimensions_singleimage_tomo==dimensions_singleimage_brightfield):     

                self.nFramesFF = self.data_brightfield.shape[0]
                self.numrowsFF = self.data_brightfield.shape[1]
                self.numcolsFF = self.data_brightfield.shape[2]


                ## Calculating the Ratios ##
                for i in range(num_exptimes_tomo):
                    self.ratios_exptimes[i] = self.exposuretimes_tomo[i]/self.averagebrightfield_exptimes
                
                for i in range(num_currents_tomo):
                    self.ratios_currents_tomo[i] = self.currents_tomo[i]/self.currents_tomo[0]
                    
                for i in range(num_currents_brightfield):
                    self.ratios_currents_brightfield[i] = self.currents_brightfield[i]/self.currents_tomo[0]
                ####    
                      
                        
                self.tomonorm['ratios']['Ratios_ExpTimes'] = self.ratios_exptimes
                self.tomonorm['ratios']['Ratios_ExpTimes'].attrs['Ratio_ExpTimes'] = 'ExposureTimesTomo[i]/Avg_FF_ExpTime'
                self.tomonorm['ratios']['Ratios_ExpTimes'].write()
                
                self.tomonorm['ratios']['Ratios_CurrentsTomo'] = self.ratios_currents_tomo
                self.tomonorm['ratios']['Ratios_CurrentsTomo'].attrs['Ratio_CurrentsTomo'] = 'CurrentsTomo[i]/CurrentsTomo[0]'
                self.tomonorm['ratios']['Ratios_CurrentsTomo'].write()
                
                self.tomonorm['ratios']['Ratios_CurrentsFF'] = self.ratios_currents_brightfield
                self.tomonorm['ratios']['Ratios_CurrentsFF'].attrs['Ratio_CurrentsFF'] = 'CurrentsFF[i]/CurrentsTomo[0]'
                self.tomonorm['ratios']['Ratios_CurrentsFF'].write()
                
                
                
                #### BrightField images normalized with current, and Average of BrightField Normalized with current ####
                self.tomonorm['FFNormalizedWithCurrent'] = nxs.NXfield(
                     name='FFNormalizedWithCurrent', dtype='float32' , shape=[nxs.UNLIMITED, self.numrowsFF, self.numcolsFF])

                self.tomonorm['FFNormalizedWithCurrent'].attrs['Number of Frames'] = self.nFramesFF
                self.tomonorm['FFNormalizedWithCurrent'].write()
                
                self.averagebright=np.empty((self.numrowsFF, self.numcolsFF), dtype=np.float)
                
                image_FF_normalized_with_current_reshape = np.empty((1,self.numrowsFF, self.numcolsFF), dtype = np.float)
                for numimgFF in range(self.nFramesFF):
                    image_FF_normalized_with_current = np.array(self.data_brightfield[numimgFF]/self.ratios_currents_brightfield[numimgFF], dtype = np.float)
                    image_FF_normalized_with_current_reshape[0] = image_FF_normalized_with_current
                    slab_offset = [numimgFF, 0, 0]
                    self.tomonorm['FFNormalizedWithCurrent'].put(image_FF_normalized_with_current_reshape, slab_offset, refresh=False)
                    self.tomonorm['FFNormalizedWithCurrent'].write()
                    print('FF Image %d has been normalized using the machine_currents' % numimgFF)                
                                   
                    self.averagebright = self.averagebright+image_FF_normalized_with_current
                    
                self.averagebright = self.averagebright/self.nFramesFF
                print('\nAverageFF has been calculated using the machine_currents\n')  
                ####
                
                

                self.tomonorm['AverageFF'] = nxs.NXfield(
                                name='AverageFF', dtype='float32' , shape=[self.numrowsFF, self.numcolsFF])
                self.tomonorm['AverageFF'] = self.averagebright
                self.tomonorm['AverageFF'].write()

                
                self.tomonorm['TomoNormalized'] = nxs.NXfield(
                                name='TomoNormalized', dtype='float32' , shape=[nxs.UNLIMITED, self.numrows, self.numcols])

                self.tomonorm['TomoNormalized'].attrs['Number of Frames'] = self.nFramesSample
                self.tomonorm['TomoNormalized'].write()

                self.input_nexusfile.opengroup('sample')
                self.input_nexusfile.opendata('data')


                self.avgnormalizedtomo = np.empty((self.numrows, self.numcols), dtype=np.float)
                
                for numimg in range (0, self.nFramesSample):

                    individual_image = self.input_nexusfile.getslab([numimg, 0, 0], [1, self.numrows, self.numcols])
                    self.normalizedtomo_singleimage = np.array((individual_image/self.ratios_currents_tomo[numimg]) / (self.averagebright*self.ratios_exptimes[numimg]), dtype = np.float32)               
                        
                    slab_offset = [numimg, 0, 0]
                    self.tomonorm['TomoNormalized'].put(self.normalizedtomo_singleimage, slab_offset, refresh=False)
                    self.tomonorm['TomoNormalized'].write()
                      
                    if (self.avgtomnorm == 1):
                        self.normalizedtomo_singleimage = np.reshape(self.normalizedtomo_singleimage, (self.numrows, self.numcols))
                        self.avgnormalizedtomo = self.avgnormalizedtomo + self.normalizedtomo_singleimage 
                    else:
                        pass
                          
                    print('Image %d has been normalized' % numimg)

                
                if (self.avgtomnorm == 1):
                    
                    self.avgnormalizedtomo = self.avgnormalizedtomo / self.nFramesSample
                    
                    self.tomonorm['AverageTomo'] = nxs.NXfield(
                                name='AverageTomo', dtype='float32' , shape=[self.numrows, self.numcols])
                    self.tomonorm['AverageTomo'] = self.avgnormalizedtomo
                    self.tomonorm['AverageTomo'].write()
                    print('\nAverage of the normalized tomo images has been calculated')
                else:
                    pass
                    
                    
                self.input_nexusfile.closedata()
                self.input_nexusfile.closegroup()
                self.input_nexusfile.close()

                print('\nTomography has been normalized taking into account the ExposureTimes and the MachineCurrents\n')

            else:
                print('\nThe dimensions of a tomography image does not correspond with the FF image dimensions')
                print('The normalization cannot be done\n')
                self.input_nexusfile.close()



        else:

            print('\nInformation about currents is NOT present in hdf5 file\n')
            
            self.input_nexusfile.opendata('data')
            infoshape = self.input_nexusfile.getinfo()
            dimensions_singleimage_tomo = (infoshape[0][1], infoshape[0][2])
            self.nFramesSample = infoshape[0][0]
            self.numrows = infoshape[0][1]
            self.numcols = infoshape[0][2]
            self.input_nexusfile.closedata()
        
            self.input_nexusfile.opendata('ExpTimes')
            self.exposuretimes_tomo = self.input_nexusfile.getdata()
            self.input_nexusfile.closedata()
            self.input_nexusfile.closegroup()

            self.input_nexusfile.opengroup('bright_field')
            self.input_nexusfile.opendata('data')
            self.data_brightfield = self.input_nexusfile.getdata()
            self.input_nexusfile.closedata()
            self.input_nexusfile.opendata('ExpTimes')
            self.exposuretimes_brightfield = self.input_nexusfile.getdata()
            self.input_nexusfile.closedata()
            self.input_nexusfile.closegroup()



            for i in range(len(self.exposuretimes_brightfield)):
                self.averagebrightfield_exptimes = self.averagebrightfield_exptimes + self.exposuretimes_brightfield[i]     
            self.averagebrightfield_exptimes = self.averagebrightfield_exptimes / len(self.exposuretimes_brightfield)


            print('BrightField Exposure Time is {0}.'.format(self.averagebrightfield_exptimes))
            
            num_exptimes_tomo = len(self.exposuretimes_tomo)       
            self.ratios_exptimes = [None]*num_exptimes_tomo

            dimensions_singleimage_brightfield = self.data_brightfield[0].shape      
            
            if (dimensions_singleimage_tomo==dimensions_singleimage_brightfield):     

                self.nFramesFF = self.data_brightfield.shape[0]
                self.numrowsFF = self.data_brightfield.shape[1]
                self.numcolsFF = self.data_brightfield.shape[2]
                
                self.averagebright=np.array(self.data_brightfield[0], dtype=np.float)
                for numimgFF in range (self.nFramesFF-1):
                    self.averagebright = self.averagebright+np.array(self.data_brightfield[numimgFF+1])
                self.averagebright = self.averagebright/self.nFramesFF

                for i in range (num_exptimes_tomo):
                    self.ratios_exptimes[i] = self.exposuretimes_tomo[i]/self.averagebrightfield_exptimes
                
                self.tomonorm['Ratios_ExpTimes'] = self.ratios_exptimes
                self.tomonorm['Ratios_ExpTimes'].write()
                

                self.tomonorm['AverageFF'] = nxs.NXfield(
                                name='AverageFF', dtype='float32' , shape=[self.numrowsFF, self.numcolsFF])
                self.tomonorm['AverageFF'] = self.averagebright
                self.tomonorm['AverageFF'].write()


                self.tomonorm['TomoNormalized'] = nxs.NXfield(
                                name='TomoNormalized', dtype='float32' , shape=[nxs.UNLIMITED, self.numrows, self.numcols])

                self.tomonorm['TomoNormalized'].attrs['Number of Frames'] = self.nFramesSample
                self.tomonorm['TomoNormalized'].write()

                self.input_nexusfile.opengroup('sample')
                self.input_nexusfile.opendata('data')


                self.avgnormalizedtomo = np.empty((self.numrows, self.numcols), dtype=np.float)
                
                for numimg in range (0, self.nFramesSample):

                    individual_image = self.input_nexusfile.getslab([numimg, 0, 0], [1, self.numrows, self.numcols])
                    self.normalizedtomo_singleimage = np.array(individual_image / (self.averagebright*self.ratios_exptimes[numimg]), dtype = np.float32)               

                    slab_offset = [numimg, 0, 0]
                    self.tomonorm['TomoNormalized'].put(self.normalizedtomo_singleimage, slab_offset, refresh=False)
                    self.tomonorm['TomoNormalized'].write()

                    if (self.avgtomnorm == 1):
                        self.normalizedtomo_singleimage = np.reshape(self.normalizedtomo_singleimage, (self.numrows, self.numcols))
                        self.avgnormalizedtomo = self.avgnormalizedtomo + self.normalizedtomo_singleimage 
                    else:
                        pass
                    
                    print('Image %d has been normalized' % numimg)
                
                if (self.avgtomnorm == 1):
                    
                    self.avgnormalizedtomo = self.avgnormalizedtomo / self.nFramesSample
                    
                    self.tomonorm['AverageTomo'] = nxs.NXfield(
                                name='AverageTomo', dtype='float32' , shape=[self.numrows, self.numcols])
                    self.tomonorm['AverageTomo'] = self.avgnormalizedtomo
                    self.tomonorm['AverageTomo'].write()
                    print('\nAverage of the normalized tomo images has been calculated\n') 
                else:
                    pass
            
                
                self.input_nexusfile.closedata()
                self.input_nexusfile.closegroup()
                self.input_nexusfile.close()


                


            else:
                print('The dimensions of a tomography image does not correspond with the FF image dimensions.')
                print('The normalization cannot be done.')
                self.input_nexusfile.close()
