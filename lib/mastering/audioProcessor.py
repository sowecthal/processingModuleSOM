from pydub import AudioSegment, effects
from scipy.io import wavfile
from scipy import signal
import numpy as np
import math

import soundfile as sf
import validator
import audioProcessorUtils as apu

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


def __verifyFormat(name: str):
    if name not in convertion_funcs.keys():
        raise AudioProcessorError("Format '%s' is not supported" % name)


def __convertFile(path: str, output_format: str):
    input_format = path.split('.')[-1]
    
    __verifyFormat(input_format)
    __verifyFormat(output_format)
    
    new_path = path.rsplit('.', 1)[0] + '.' + output_format
    
    output_signal = convertion_funcs[input_format](path)
    output_signal = output_signal.normalize()
    output_signal.export(new_path, format=output_format)    
    
    return new_path


def __workingInFormat(target_format):
    def prepareFileForFunction(func):
        def preparator(*args):
            path = args[0]
            converted_path = path
            if path.split('.')[-1] != target_format:
                converted_path = __convertFile(path, target_format)
            
            returned_path = func(converted_path, *args[1:])
            
            if returned_path != path:
                __convertFile(returned_path, path.split('.')[-1])
                
        return preparator
    return prepareFileForFunction


@__workingInFormat("wav")
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


def byReference(targ_path: str, ref_path: str):
    
    targ_data, targ_rate  = sf.read(targ_path, always_2d=True)
    ref_data, ref_rate = sf.read(ref_path, always_2d=True)

    targ_data, targ_rate = validator.check(targ_data, targ_rate)
    ref_data, ref_rate = validator.check(ref_data, ref_rate)

    targ_mid, targ_side = apu.convertFromLeftRightToMidSide(targ_data) 
    targ_pieces_quantity, targ_piece_size = apu.calculatePiecesParams(targ_mid, targ_rate)
    targ_loudest_RMS, targ_mid_loudest_pieces, targ_side_loudest_pieces = apu.getLoudestMidSidePieces(targ_mid, targ_side, targ_pieces_quantity, targ_piece_size)

    print(targ_pieces_quantity, targ_piece_size)

    ref_mid, ref_side = apu.convertFromLeftRightToMidSide(ref_data) 
    ref_pieces_quantity, ref_piece_size = apu.calculatePiecesParams(ref_mid, ref_rate)
    ref_loudest_RMS, ref_mid_loudest_pieces, ref_side_loudest_pieces = apu.getLoudestMidSidePieces(ref_mid, ref_side, ref_pieces_quantity, ref_piece_size)

    print(ref_pieces_quantity, ref_piece_size)

    rms_coefficient, targ_mid, targ_side = apu.calculateCoefficientAndAmplify(targ_mid, targ_side, targ_loudest_RMS, ref_loudest_RMS)    

    targ_mid_loudest_pieces *= rms_coefficient
    targ_side_loudest_pieces *= rms_coefficient

    mid_fir = apu.getFIR(targ_mid_loudest_pieces, ref_mid_loudest_pieces)
    side_fir = apu.getFIR(targ_side_loudest_pieces, ref_side_loudest_pieces)

    result, result_mid = apu.convolve(targ_mid, mid_fir, targ_side, side_fir)

    sf.write(targ_path, result, targ_rate)

