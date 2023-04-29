from pydub import AudioSegment, effects
from scipy.io import wavfile
from scipy import signal
import numpy as np
import math

convertion_funcs = {
    'wav': AudioSegment.from_wav,
    'mp3': AudioSegment.from_mp3,
    'ogg': AudioSegment.from_ogg
}

class AudioProcessorError(Exception):
    def __init__(self, message: str):
        self.message = str(message)
    
    def __str__(self):
        return self.message
        

def verifyFormat(name: str):
    if name not in convertion_funcs.keys():
        raise AudioProcessorError("Format '%s' is not supported" % name)

def workingInFormat(target_format):
    def prepareFileForFunction(func):
        def preparator(*args):
            path = args[0]
            converted_path = path
            if path.split('.')[-1] != target_format:
                converted_path = convertFile(path, target_format)
            
            returned_path = func(converted_path, *args[1:])
            
            if returned_path != path:
                convertFile(returned_path, path.split('.')[-1])
                
        return preparator
    return prepareFileForFunction


def convertFile(path: str, output_format: str):
    input_format = path.split('.')[-1]
    
    verifyFormat(input_format)
    verifyFormat(output_format)
    
    new_path = path.rsplit('.', 1)[0] + '.' + output_format
    
    output_signal = convertion_funcs[input_format](path)
    output_signal = output_signal.normalize()
    output_signal.export(new_path, format=output_format)    
    
    return new_path


def calculatePieceSizes(data: np.ndarray, rate: int, max_piece_duration=15):
    array_size = data.shape[0]
    piece_duration = rate * max_piece_duration
    num_pieces = math.ceil(array_size / piece_duration)
    last_piece_size = array_size - (num_pieces - 1) * piece_duration #last piece length in samples 

    print(f"\nThe audio file will be divided into {num_pieces} pieces.")
    pieces_borders = []
    for i in range(num_pieces-1):
        piece_start = i * piece_duration
        piece_end = piece_start + piece_duration
        pieces_borders.append((piece_start, piece_end))
        print(f"Piece {i+1} starts at {piece_start / rate:.2f} seconds and ends at {piece_end / rate:.2f} seconds.")

    if last_piece_size > 0:
        piece_start = (num_pieces-1) * piece_duration
        piece_end = piece_start + last_piece_size
        pieces_borders.append((piece_start, piece_end))
        print(f"Last piece starts at {piece_start / rate:.2f} seconds and ends at {piece_end / rate:.2f} seconds.\n")
    else:
        print("The last piece has a length of 0 seconds.")

    return array_size, num_pieces, piece_duration, last_piece_size, pieces_borders


def getSegments(data: np.ndarray, pieces_borders: list) -> dict:
    segments = {}
    for i, piece_borders in enumerate(pieces_borders):
        start, end = piece_borders
        segments[i] = data[start:end, :]
    
    return segments
    

def calculateSegmentsRMS(segments: dict):
    rms_values = np.zeros(len(segments.keys()))
    
    for i, segment in enumerate(list(segments.values())): 
        segment_data = segment.astype(np.int32)
        rms_values[i] = np.sqrt(np.mean(np.square(segment_data)))
        print(f"The {i}th piece has an RMS of {rms_values[i]}.\n")
    
    return rms_values


def calculateCoefficientAndAmplify(target_average: float, ref_average: float, target_greater_rms_values: dict, target_segments: dict):
    rms_coefficient = ref_average / target_average
    print(f"\nThe RMS coefficient is: {rms_coefficient}")
    
    for key in target_greater_rms_values.keys():
        target_segments[key] = target_segments[key] * rms_coefficient
    print(f"Greater than average target RMS after amplifying are {target_segments}")


def modifyRMS(targ_path, ref_path):
    if targ_path:
        rate, data = wavfile.read(targ_path)
        *_, pieces_borders = calculatePieceSizes(data, rate)
        target_segments = getSegments(data, pieces_borders)
        
        target_rms_values = calculateSegmentsRMS(target_segments)
        
        target_average = np.mean(target_rms_values)
        print(f"Average target RMS is {target_average}.")
        
        target_rms_dict = {inx: val for inx, val in enumerate(target_rms_values)}
        print(f"Initial target RMS are {target_rms_dict}")
        
        target_greater_rms_values = {inx: val for inx, val in enumerate(target_rms_values) if val>target_average}
        print(f"Greater than average target RMS are {target_greater_rms_values}")
        
        target_greater_average = np.mean(list(target_greater_rms_values.values()))
        print(f"Average of greater than average target RMS are {target_greater_average}")
    
    if ref_path:
        rate, data = wavfile.read(ref_path)
        *_, pieces_borders = calculatePieceSizes(data, rate)
        ref_segments = getSegments(data, pieces_borders)
        
        ref_rms_values = calculateSegmentsRMS(ref_segments)
        
        ref_average = np.mean(ref_rms_values)
        print(f"Reference average RMS is {ref_average}.")
        
        ref_rms_dict = {inx: val for inx, val in enumerate(ref_rms_values)}
        print(f"Initial reference RMS are {ref_rms_dict}")
        
        ref_greater_rms_values = {inx: val for inx, val in enumerate(ref_rms_values) if val>ref_average}
        print(f"Greater than average reference RMS are {ref_greater_rms_values}")
        
        ref_greater_average = np.mean(list(ref_greater_rms_values.values()))
        print(f"Average of greater than average reference RMS are {ref_greater_average}")
    
    print(f"Greater than average target RMS before amplifying are {target_segments}")

    calculateCoefficientAndAmplify(target_greater_average, ref_greater_average, target_greater_rms_values, target_segments)


@workingInFormat("wav")
def equalizeFile(path: str, low_gain: float, mid_gain: float, high_gain: float): 
    rate, data = wavfile.read(path)

    low = 200   
    high = 5000

    b_low, a_low = signal.butter(6, low, 'lowpass', fs=rate)
    b_mid, a_mid = signal.butter(6, [low, high], 'bandpass', fs=rate)
    b_high, a_high = signal.butter(6, high, 'highpass', fs=rate)

    low_signal = signal.filtfilt(b_low, a_low, data, padlen=0)
    mid_signal = signal.filtfilt(b_mid, a_mid, data, padlen=0)
    high_signal = signal.filtfilt(b_high, a_high, data, padlen=0)
    
    low_signal *= low_gain
    mid_signal *= mid_gain
    high_signal *= high_gain

    output_signal = low_signal + mid_signal + high_signal
    
    wavfile.write(path, rate, output_signal.astype(np.int16))
    return path

def compressFile(path: str, threshold: float, ratio: float, attack=5.0, release=50.0):
    input_signal = AudioSegment.from_file(path, path.split('.')[-1])
    print("RMS level before compression: ", input_signal.rms)

    output_signal = input_signal.compress_dynamic_range(threshold=threshold, ratio=ratio, attack=attack, release=release)
    print("RMS level after compression: ", output_signal.rms)
    
    output_signal.export(path, format=path.split('.')[-1])
    return path

def normalizeFile(path: str, multiplier=None, dBFS=None):
    input_signal = AudioSegment.from_file(path, path.split('.')[-1])
    print("dBFS before normalization: ", round(input_signal.dBFS, 1))

    if not (multiplier or dBFS):
        output_signal = effects.normalize(input_signal)
        print("dBFS after normalization: ", round(output_signal.dBFS, 1))
    else:
        target_dBFS = dBFS if dBFS else round(input_signal.dBFS, 1) * multiplier
        delta_dBFS = target_dBFS - input_signal.dBFS
        output_signal = input_signal.apply_gain(delta_dBFS)
        print("dBFS after normalization: ", round(output_signal.dBFS, 1))

    output_signal.export(path, format=path.split('.')[-1])
    return path

@workingInFormat("wav")
def byReference(path: str, ref_path: str):
    def getReferenceParams(ref_path: str) -> dict:
        pass
        # params = {}
        # input_signal = AudioSegment.from_file(ref_path, ref_path.split('.')[-1])
        # params['dBFS'] = round(input_signal.dBFS, 1)
        # return params

    def applyReferenceParams(path: str, params: dict):
        pass
        # normalizeFile(path, dBFS=params['dBFS'])
    
    applyReferenceParams(path, getReferenceParams(ref_path))
