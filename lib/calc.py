from pydub import AudioSegment, effects
from scipy.io import wavfile
from scipy import signal
import numpy as np
import math
import statsmodels.api as sm
from freqamp import getFIR, convolve
    
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
    

def calculateSegmentsRMS(segments: dict) -> np.array:
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
    
    target_list = np.vstack(list(target_segments.values()))
    print("target",target_list)
    return target_list


def extractLoudestPieces(segments: dict, greater_rms_values: dict) -> list:
    loudest_pieces = {inx: vals for inx, vals in segments.items() if inx in greater_rms_values.keys()}
    loudest_pieces_list = np.vstack(list(loudest_pieces.values()))
    
    print("loudest",loudest_pieces_list.shape)
    return loudest_pieces_list


def getAverageRMS(segments: dict) -> tuple:    
    rms_values = calculateSegmentsRMS(segments)

    average = np.mean(rms_values)
    print(f"Average RMS is {average}.")
    
    rms_values_dict = {inx: val for inx, val in enumerate(rms_values)}
    print(f"Initial RMS are {rms_values_dict}")
    
    greater_rms_values = {inx: val for inx, val in enumerate(rms_values) if val>average}
    print(f"Greater than average RMS are {greater_rms_values}")
    
    greater_average = np.mean(list(greater_rms_values.values()))
    print(f"Average of greater than average RMS are {greater_average}")
    
    return greater_rms_values, greater_average
    
   
def byReference(targ_path: str, ref_path: str):
    if targ_path:
        rate, data = wavfile.read(targ_path)
        *_, pieces_borders = calculatePieceSizes(data, rate)
        target_segments = getSegments(data, pieces_borders)
        target_greater_rms_values, target_greater_average = getAverageRMS(target_segments)
        target_loudest_pieces = extractLoudestPieces(target_segments, target_greater_rms_values)
        
    if ref_path:
        rate, data = wavfile.read(ref_path)
        *_, pieces_borders = calculatePieceSizes(data, rate)
        ref_segments = getSegments(data, pieces_borders)
        ref_greater_rms_values, ref_greater_average = getAverageRMS(ref_segments)
        ref_loudest_pieces = extractLoudestPieces(ref_segments, ref_greater_rms_values)
    
    output_signal = calculateCoefficientAndAmplify(target_greater_average, ref_greater_average, target_greater_rms_values, target_segments)
    path = targ_path.rsplit('.', 1)[0] + '_amp.wav'
    wavfile.write(path, rate, output_signal.astype(np.int16))
    
    fir = getFIR(target_loudest_pieces, ref_loudest_pieces)
  
if __name__ == '__main__':
    byReference('s.wav', 'm.wav')