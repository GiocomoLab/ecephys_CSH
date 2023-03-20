from argschema import ArgSchema
from argschema.schemas import DefaultSchema
from argschema.fields import Nested, String, Float, Int
from ...common.schemas import EphysParams, Directories, ClusterMetricsFile, WaveformMetricsFile


class PrePhyFilterParams(DefaultSchema):
    
    snr_min = Float(required=False, default=2, help='Min SNR for non-noise clusters')
    halfwidth_max = Float(required=False, default=0.3, help='Max halfwidth for non-noise clusters')
    wide_halfwidth_max = Float(required=False, default=0.3, help='Max halfwidth (combined with repo_slope) for non-noise clusters')
    repo_slope = Float(required=False, default=0.05, help='Min repolarization slope for wide, non-noise clusters')
    mua_fr_min = Float(required=False, default=0.01, help='Min FR for non-noise clusters')
    depth = Int(required=False, default=3200, help='Depth (microns) from probe tip to brain surface')
    isi_viol_max = Float(required=False, default=0.2, help='Max % ISI violations')
    contam_rate_max = Float(required=False, default=15, help='Max contamination rate for good clusters')
    good_fr_min = Float(required=False, default=0.05, help='Min FR for good clusters')

class InputParameters(ArgSchema):
    
    prephy_filters_params = Nested(PrePhyFilterParams)
    ephys_params = Nested(EphysParams)
    directories = Nested(Directories)
    cluster_metrics = Nested(ClusterMetricsFile)
    waveform_metrics = Nested(WaveformMetricsFile)
    
class OutputSchema(DefaultSchema): 
    input_parameters = Nested(InputParameters, 
                              description=("Input parameters the module " 
                                           "was run with"), 
                              required=True) 
 
class OutputParameters(OutputSchema): 

    execution_time = Float()
    quality_metrics_output_file = String()