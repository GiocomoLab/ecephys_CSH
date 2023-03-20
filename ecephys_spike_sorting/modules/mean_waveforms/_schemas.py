from argschema import ArgSchema, ArgSchemaParser 
from argschema.schemas import DefaultSchema
from argschema.fields import Nested, InputDir, String, Float, Dict, Int, Bool
from ...common.schemas import EphysParams, Directories, WaveformMetricsFile, ClusterMetricsFile

class MeanWaveformParams(DefaultSchema):
    samples_per_spike = Int(required=True, default=82, help='Number of samples to extract for each spike')
    pre_samples = Int(required=True, default=20, help='Number of samples between start of spike and the peak')
    num_epochs = Int(required=True, default=1, help='Number of epochs to compute mean waveforms')
    spikes_per_epoch = Int(require=True, default=100, help='Max number of spikes per epoch')
    upsampling_factor = Float(require=False, default=200/82, help='Upsampling factor for calculating waveform metrics')
    spread_threshold = Float(require=False, default=0.12, help='Threshold for computing channel spread of 2D waveform')
    site_range = Int(require=False, default=16, help='Number of sites to use for 2D waveform metrics')
    cWaves_path = InputDir(require=False, help='directory containing the TPrime executable.')
    use_C_Waves = Bool(require=False, default=False, help='Use faster C routine to calculate mean waveforms')
    snr_radius = Int(require=False, default=8, help='disk radius (chans) about pk-chan for snr calculation in C_waves')
    mean_waveforms_file = String(required=True, help='Path to mean waveforms file (.npy)')


class InputParameters(ArgSchema):
    
    waveform_metrics = Nested(WaveformMetricsFile)
    mean_waveform_params = Nested(MeanWaveformParams)
    cluster_metrics = Nested(ClusterMetricsFile)
    ephys_params = Nested(EphysParams)
    directories = Nested(Directories)

class OutputSchema(DefaultSchema): 
    input_parameters = Nested(InputParameters, 
                              description=("Input parameters the module " 
                                           "was run with"), 
                              required=True) 
 
class OutputParameters(OutputSchema): 

    execution_time = Float()
    mean_waveforms_file = String()
    