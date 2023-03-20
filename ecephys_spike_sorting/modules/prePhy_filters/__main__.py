"""
Additional module written by Emily Aery Jones, 19 May 2022; edited by Charlotte Herber March 2023
"""
from argschema import ArgSchemaParser
import os
import time
import numpy as np
import pandas as pd

from ...common.utils import write_cluster_group_tsv, getFileVersion


def filter_by_metrics(args):

    print('ecephys spike sorting: pre-Phy filters module')

    start = time.time()

    # find the correct metrics file (eg metrics.csv, metrics_1.csv, ...)
    metrics_file_args = args['cluster_metrics']['cluster_metrics_file']
    metrics_file, version = getFileVersion(metrics_file_args)
        
    waveform_metrics_file_args = args['waveform_metrics']['waveform_metrics_file']
    waveform_metrics_file, version = getFileVersion(waveform_metrics_file_args)
    
    # read the metrics files and join with waveforms if previous module failed to
    metrics = pd.read_csv(metrics_file)
    if 'snr' not in metrics.columns:
        waveform_metrics = pd.read_csv(waveform_metrics_file)
        metrics = metrics.merge(waveform_metrics, left_on='cluster_id', right_on='cluster_id')
    
    # read cluster assignments
    clusters_file = os.path.join(args['directories']['kilosort_output_directory'], \
                args['ephys_params']['cluster_group_file_name'])
    clusters = pd.read_csv(clusters_file, sep='\t')
    
    # load channels for each cluster to get depths
    cluster_map = np.load(os.path.join(args['directories']['kilosort_output_directory'], \
                                       'clus_Table.npy'))
    # remove clusters without spikes
    cluster_map = cluster_map[~(cluster_map[:,0] == 0)]
        
    # convert from channel # to depth (floor(ch/2+1)*20)
    depths = cluster_map[:,1]/2+1
    depths = depths.astype(int)
    metrics['depth'] = depths*20
        
    # save a copy of the original labels
    clusters_original = clusters.rename(columns={'group':'original_group'})
    clusters_original.to_csv(clusters_file[:-4]+'_original.tsv', sep='\t', index=False)
    
    # change the labels that meet MUA filters
    labels = [ ]
    mua_clusters = 0
    noise_clusters = 0
    good_clusters = 0
    
    for i, row in metrics.iterrows():
        # start with original label; overwrite 
        label = clusters['group'].loc[clusters['cluster_id']==row['cluster_id']].item()
        
        # find noise clusters
        
        # for HPC: allow wider waveforms as long as they are not too flat
        if args['prephy_filters_params']['halfwidth_max'] < args['prephy_filters_params']['wide_halfwidth_max']:
            if (row['halfwidth'] > args['prephy_filters_params']['halfwidth_max']) & \
                (row['halfwidth'] < args['prephy_filters_params']['wide_halfwidth_max']):
                    if row['repolarization_slope'] < args['prephy_filters_params']['repo_slope']:
                        label = 'noise'
                        noise_clusters += 1
                        
        if ((row['snr']<args['prephy_filters_params']['snr_min']) | \
            (row['halfwidth']>args['prephy_filters_params']['wide_halfwidth_max']) | \
            (row['firing_rate']<args['prephy_filters_params']['mua_fr_min']) | \
            (row['depth']>args['prephy_filters_params']['depth'])):
                label = 'noise'
                noise_clusters += 1

        # "rescue" MUA designated units that meet these criteria        
        elif (label=='mua') & \
            ((row['isi_viol'] <= args['prephy_filters_params']['isi_viol_max']) & \
            (row['contam_rate'] <= args['prephy_filters_params']['contam_rate_max']) & \
            (row['firing_rate'] >= args['prephy_filters_params']['mua_fr_min'])):
                label = 'good'
                good_clusters += 1

                labels.append(label)

                continue

        # label good units MUA if they meet these criteria (adjusted num viol allowed up from 1 to 3, allowed lower FR due to longer sessions)     
        elif (label=='good') & \
            (((row['isi_viol'] > args['prephy_filters_params']['isi_viol_max']) & (row['num_viol']>3)) | \
            (row['contam_rate'] > args['prephy_filters_params']['contam_rate_max']) | \
            (row['firing_rate'] < args['prephy_filters_params']['mua_fr_min'])):
                label = 'mua'
                mua_clusters += 1

        labels.append(label)

    # write output
    write_cluster_group_tsv(metrics['cluster_id'], 
    						labels, 
    						args['directories']['kilosort_output_directory'], 
    						args['ephys_params']['cluster_group_file_name'])
    print(f'Reclassified {mua_clusters} good clusters as MUA, {good_clusters} MUA clusters as good, and {noise_clusters} clusters as noise from {len(metrics)} clusters')
    
    execution_time = time.time() - start
    print('total time: ' + str(np.around(execution_time,2)) + ' seconds')
    print()
    
    return {"execution_time" : execution_time,
            "quality_metrics_output_file" : args['cluster_metrics']['cluster_metrics_file']} # output manifest

def main():

    from ._schemas import InputParameters, OutputParameters

    mod = ArgSchemaParser(schema_type=InputParameters,
                          output_schema_type=OutputParameters)

    output = filter_by_metrics(mod.args)

    output.update({"input_parameters": mod.args})
    if "output_json" in mod.args:
        mod.output(output, indent=2)
    else:
        print(mod.get_output_json(output))


if __name__ == "__main__":
    main()
