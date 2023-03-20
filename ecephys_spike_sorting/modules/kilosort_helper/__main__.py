import matlab.engine   # on some systems, the matlab engine must be loaded first

from argschema import ArgSchemaParser
import os
import time
import shutil

import numpy as np



from pathlib import Path

from scipy.signal import butter, filtfilt, medfilt

from . import matlab_file_generator
from ...common.SGLXMetaToCoords import MetaToCoords
from ...common.utils import read_probe_json, get_repo_commit_date_and_hash, rms

def run_kilosort(args):

    print('ecephys spike sorting: kilosort helper module')

    print('master branch -- single main KS2/KS25/KS3')


    commit_date, commit_time = get_repo_commit_date_and_hash(args['kilosort_helper_params']['kilosort_repository'])

    input_file = args['ephys_params']['ap_band_file']
    input_file_forward_slash = input_file.replace('\\','/')

    output_dir = args['directories']['kilosort_output_directory']
    output_dir_forward_slash = output_dir.replace('\\','/')
    

    mask = get_noise_channels(args['ephys_params']['ap_band_file'],
                              args['ephys_params']['num_channels'],
                              args['ephys_params']['sample_rate'],
                              args['ephys_params']['bit_volts'])
     
    
    if args['kilosort_helper_params']['spikeGLX_data']:
       # SpikeGLX data, will build KS chanMap based on the metadata file plus 
       # exclusion of noise channels found in get_noise_channels
       # metadata file must be in the same directory as the ap_band_file
       # resulting chanmap is copied to the matlab home directory, and will 
       # overwrite any existing 'chanMap.mat'
       metaName, binExt = os.path.splitext(args['ephys_params']['ap_band_file'])
       metaFullPath = Path(metaName + '.meta')

       destFullPath = os.path.join(args['kilosort_helper_params']['matlab_home_directory'], 'chanMap.mat')
       MaskChannels = np.where(mask == False)[0]      
       MetaToCoords( metaFullPath=metaFullPath, outType=1, badChan=MaskChannels, destFullPath=destFullPath)
       # end of SpikeGLX block
       
    else:
        # Open Ephys data, specifically finding the tissue surface and creating a chanMap to 
        # exclude those channels. Assumes 3A/NP1.0 site geometry, all sites in bank 0.
        _, offset, scaling, surface_channel, air_channel = read_probe_json(args['common_files']['probe_json'])
        
        mask[args['ephys_params']['reference_channels']] = False
    
        top_channel = np.min([args['ephys_params']['num_channels'], int(surface_channel) + args['kilosort_helper_params']['surface_channel_buffer']])
        
        matlab_file_generator.create_chanmap(args['kilosort_helper_params']['matlab_home_directory'], \
                                            EndChan = top_channel, \
                                            probe_type = args['ephys_params']['probe_type'],
                                            MaskChannels = np.where(mask == False)[0])
        # end of Open Ephys block    
    

# copy the msster fle to the same directory that contains the channel map and config file
#    master_fullpath = os.path.join(os.path.join(args['kilosort_helper_params']['master_file_path'],args['kilosort_helper_params']['master_file_name']))
        
#    shutil.copyfile(master_fullpath,
#            os.path.join(args['kilosort_helper_params']['matlab_home_directory'],args['kilosort_helper_params']['master_file_name']))
    shutil.copyfile(os.path.join(args['directories']['ecephys_directory'],'modules','kilosort_helper','main_kilosort_multiversion.m'),
        os.path.join(args['kilosort_helper_params']['matlab_home_directory'],'main_kilosort_multiversion.m'))
    
    if args['kilosort_helper_params']['kilosort_version'] == 1:
    
        matlab_file_generator.create_config(args['kilosort_helper_params']['matlab_home_directory'], 
                                            input_file_forward_slash, 
                                            os.path.basename(args['ephys_params']['ap_band_file']), 
                                            args['kilosort_helper_params']['kilosort_params'])
    
    elif args['kilosort_helper_params']['kilosort_version'] == 2:
    
        matlab_file_generator.create_config2(args['kilosort_helper_params']['matlab_home_directory'], 
                                             output_dir_forward_slash, 
                                             input_file_forward_slash,
                                             args['ephys_params'], 
                                             args['kilosort_helper_params']['kilosort2_params'])
    else:
        print('unknown kilosort version')
        return

    start = time.time()
    
    eng = matlab.engine.start_matlab()
    
#    if ~args['kilosort_helper_params']['spikeGLX_data']:
#        # Create channel map from Open Ephys parameters through a matlab call
#        eng.createChannelMapFile(nargout=0)

# jic -- remove call to config file, should be called from kilsort_master
# jic -- add paths to kilosort repo and matlab home directory
#
#  
    KS_dir = args['kilosort_helper_params']['kilosort_repository'].replace('\\','/')
    NPY_dir = args['kilosort_helper_params']['npy_matlab_repository'].replace('\\','/')
    home_dir = args['kilosort_helper_params']['matlab_home_directory'].replace('\\','/')
      
    
            
    if args['kilosort_helper_params']['kilosort_version'] == 1:    
        eng.addpath(eng.genpath(KS_dir))
        eng.addpath(eng.genpath(NPY_dir))
        eng.addpath(home_dir)
        eng.kilosort_master_file(nargout=0)
    else:
        eng.addpath(eng.genpath(KS_dir))
        eng.addpath(eng.genpath(NPY_dir))
        eng.addpath(home_dir)      
        eng.main_kilosort_multiversion(args['kilosort_helper_params']['kilosort2_params']['KSver'], \
                          args['kilosort_helper_params']['kilosort2_params']['remDup'], \
                          args['kilosort_helper_params']['kilosort2_params']['finalSplits'], \
                          args['kilosort_helper_params']['kilosort2_params']['labelGood'], \
                          args['kilosort_helper_params']['kilosort2_params']['saveRez'], \
                          nargout=0)
        

    # set dat_path in params.py
    #    if the user has not requested a copy of the procecess temp_wh file
    # set to relative path to the original input binary; set the number of channels
    # to number of channels in the input
    #    if the user has rquested a copy of the processed temp_wh, copy that file
    # to the input directory and set dat_path to point to it. Set the number of 
    # channls in the processed file
    dat_dir, dat_name = os.path.split(input_file)
    
    copy_fproc = args['kilosort_helper_params']['kilosort2_params']['copy_fproc']
  
    if copy_fproc:
        fproc_path_str = args['kilosort_helper_params']['kilosort2_params']['fproc']
        # trim quotes off string sent to matlab
        fproc_path = fproc_path_str[1:len(fproc_path_str)-1]
        fp_dir, fp_name = os.path.split(fproc_path)
        # make a new name for the processed file based on the original
        # binary and metadata files
        fp_save_name = metaName + '_ksproc.bin'
        shutil.copy(fproc_path, os.path.join(dat_dir, fp_save_name))
        cm_path = os.path.join(output_dir, 'channel_map.npy')
        cm = np.load(cm_path)
        chan_phy_binary = cm.size
        fix_phy_params(output_dir, dat_dir, fp_save_name, chan_phy_binary, args['ephys_params']['sample_rate'])
    else:
        chan_phy_binary = args['ephys_params']['num_channels']
        fix_phy_params(output_dir, dat_dir, dat_name, chan_phy_binary, args['ephys_params']['sample_rate'])                

    # make a copy of the channel map to the data directory
    # named according to the binary and meta file
    # alredy have path to chanMap = destFullPath
    cm_save_name = metaName + '_chanMap.mat'
    shutil.copy(destFullPath, os.path.join(dat_dir, cm_save_name))

    if args['kilosort_helper_params']['ks_make_copy']:
        # get the kilsort output directory name
        pPath, phyName = os.path.split(output_dir)
        # build a name for the copy
        copy_dir = os.path.join(pPath, phyName + '_orig')
        # check for whether the directory is already there; if so, delete it
        if os.path.exists(copy_dir):
            shutil.rmtree(copy_dir)
        # make a copy of output_dir
        shutil.copytree(output_dir, copy_dir)

    execution_time = time.time() - start

    print('kilsort run time: ' + str(np.around(execution_time, 2)) + ' seconds')
    print()
    
    # Don't call getSortResults until after any postprocessing
    # but get useful characteristics of ksort output right now
    spkTemplate = np.load(os.path.join(output_dir,'spike_templates.npy'))
    nTemplate = np.unique(spkTemplate).size
    nTot = spkTemplate.size
       
    return {"execution_time" : execution_time,
            "kilosort_commit_date" : commit_date,
            "kilosort_commit_hash" : commit_time,
            "mask_channels" : np.where(mask == False)[0],
            "nTemplate" : nTemplate,
            "nTot" : nTot } # output manifest

def get_noise_channels(raw_data_file, num_channels, sample_rate, bit_volts, noise_threshold=20):

    noise_delay = 5            #in seconds
    noise_interval = 10         #in seconds
    
    raw_data = np.memmap(raw_data_file, dtype='int16')
    
    num_samples = int(raw_data.size/num_channels)
      
    data = np.reshape(raw_data, (num_samples, num_channels))
   
    start_index = int(noise_delay * sample_rate)
    end_index = int((noise_delay + noise_interval) * sample_rate)
    
    if end_index > num_samples:
        print('noise interval larger than total number of samples')
        end_index = num_samples
        
    uplim = 10000/(sample_rate/2);
    if uplim >= 1:
        uplim = 0.99;
    
    b, a = butter(3, [10/(sample_rate/2), uplim], btype='band')

    D = data[start_index:end_index, :] * bit_volts
    
    D_filt = np.zeros(D.shape)  # datatype set by D

    for i in range(D.shape[1]):
        D_filt[:,i] = filtfilt(b, a, D[:,i])

    rms_values = np.apply_along_axis(rms, axis=0, arr=D_filt)

    above_median = rms_values - medfilt(rms_values,11)
    
    print('number of noise channels: ' + repr(sum(above_median > noise_threshold)))

    return above_median < noise_threshold

def fix_phy_params(output_dir, dat_path, dat_name, chan_phy_binary, sample_rate):

    # write a new params.py file. 
    # dat_path will be set to a relative path from output_dir to
    # dat_path/dat_name
    # sample rate will be written out to sufficient digits to be used
    
    shutil.copy(os.path.join(output_dir,'params.py'), os.path.join(output_dir,'old_params.py'))
    
    relPath = os.path.relpath(dat_path, output_dir)
    new_path = os.path.join(relPath, dat_name)
    new_path = new_path.replace('\\','/')
    
    paramLines = list()
    
    with open(os.path.join(output_dir,'old_params.py'), 'r') as f:
        currLine = f.readline()
        
        while currLine != '':  # The EOF char is an empty string
            if 'dat_path' in currLine:
                currLine = "dat_path = '" + new_path + "'\n"
            elif 'n_channels_dat' in currLine:
                currLine = "n_channels_dat = " + repr(chan_phy_binary) + "\n"
            elif 'sample_rate' in currLine:
                currLine = (f'sample_rate = {sample_rate:.12f}\n')
            paramLines.append(currLine)           
            currLine = f.readline()
            
    with open(os.path.join(output_dir,'params.py'), 'w') as fout:
        for line in paramLines:
            fout.write(line)

def main():

    from ._schemas import InputParameters, OutputParameters

    """Main entry point:"""
    mod = ArgSchemaParser(schema_type=InputParameters,
                          output_schema_type=OutputParameters)

    output = run_kilosort(mod.args)

    output.update({"input_parameters": mod.args})
    if "output_json" in mod.args:
        mod.output(output, indent=2)
    else:
        print(mod.get_output_json(output))


if __name__ == "__main__":
    main()
