from pydub import AudioSegment, effects
from scipy.io import wavfile
from scipy import signal
import soundfile as sf
import numpy as np
import logging

from . import validator
from . import audioProcessorUtils as apu


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
        def preparator(*args, **kwargs):
            path = args[0]
            current_format = path.split('.')[-1]
            convertion_is_required = True if current_format != target_format else False

            if convertion_is_required:
                path = __convertFile(path, target_format)
            
            path = func(path, *args[1:], **kwargs)

            if convertion_is_required:
                path = __convertFile(path, current_format)
            
            return path
        return preparator
    return prepareFileForFunction


@__workingInFormat("wav")
def equalizeFile(path: str, eq_dict: dict): #test dictionary = {200: 10, 1000: -10, 5000: -10}
    rate, data = wavfile.read(path)

    if len(data.shape) > 1 and data.shape[1] > 1:
        data_left = data[:, 0]
        data_right = data[:, 1]
    else:
        data_left = data_right = data

    output_signal_left = np.array(data_left, dtype=np.float64)
    output_signal_right = np.array(data_right, dtype=np.float64)

    for freq in eq_dict.keys():
        gain_db = eq_dict[freq]
        gain = 10**(gain_db/20)

        b, a = signal.butter(2, [0.9*freq, 1.1*freq], 'bandpass', fs=rate)

        band_left = signal.filtfilt(b, a, data_left)
        band_right = signal.filtfilt(b, a, data_right)

        output_signal_left += gain * band_left - band_left
        output_signal_right += gain * band_right - band_right

    output_signal_left /= np.max(np.abs(output_signal_left))
    output_signal_right /= np.max(np.abs(output_signal_right))

    output_signal = np.vstack((output_signal_left, output_signal_right)).T

    output_signal = np.int16(output_signal * 32767)

    new_path = path.rsplit('.', 1)[0] + '_eq.' + path.split('.')[-1]
    wavfile.write(new_path, rate, output_signal)
    return new_path


def compressFile(path: str, *, threshold = -20.0, ratio = 4.0, attack = 5.0, release = 50.0):
    input_signal = AudioSegment.from_file(path, path.split('.')[-1])
    output_signal = input_signal.compress_dynamic_range(threshold=threshold, ratio=ratio, attack=attack, release=release)
    
    new_path = path.rsplit('.', 1)[0] + '_comp.'+ path.split('.')[-1]
    output_signal.export(new_path)

    return new_path


def normalizeFile(path: str, dBFS=None):
    input_signal = AudioSegment.from_file(path, path.split('.')[-1])
    
    if not dBFS:
        output_signal = effects.normalize(input_signal)
    else:
        delta_dBFS = dBFS - input_signal.dBFS
        output_signal = input_signal.apply_gain(delta_dBFS)

    new_path = path.rsplit('.', 1)[0] + '_norm.'+ path.split('.')[-1]
    output_signal.export(new_path)
    
    return new_path


def byReference(targetTrack: str, referenceTrack: str):
    
    targ_data, targ_rate  = sf.read(targetTrack, always_2d=True)
    ref_data, ref_rate = sf.read(referenceTrack, always_2d=True)

    targ_data, targ_rate = validator.check(targ_data, targ_rate)
    ref_data, ref_rate = validator.check(ref_data, ref_rate)

    targ_mid, targ_side = apu.convertFromLeftRightToMidSide(targ_data) 
    targ_pieces_quantity, targ_piece_size = apu.calculatePiecesParams(targ_mid, targ_rate)
    targ_loudest_RMS, targ_mid_loudest_pieces, targ_side_loudest_pieces = apu.getLoudestMidSidePieces(targ_mid, targ_side, targ_pieces_quantity, targ_piece_size)

    ref_mid, ref_side = apu.convertFromLeftRightToMidSide(ref_data) 
    ref_pieces_quantity, ref_piece_size = apu.calculatePiecesParams(ref_mid, ref_rate)
    ref_loudest_RMS, ref_mid_loudest_pieces, ref_side_loudest_pieces = apu.getLoudestMidSidePieces(ref_mid, ref_side, ref_pieces_quantity, ref_piece_size)

    rms_coefficient, targ_mid, targ_side = apu.calculateCoefficientAndAmplify(targ_mid, targ_side, targ_loudest_RMS, ref_loudest_RMS)    

    targ_mid_loudest_pieces *= rms_coefficient
    targ_side_loudest_pieces *= rms_coefficient

    mid_fir = apu.getFIR(targ_mid_loudest_pieces, ref_mid_loudest_pieces)
    side_fir = apu.getFIR(targ_side_loudest_pieces, ref_side_loudest_pieces)

    result, result_mid = apu.convolve(targ_mid, mid_fir, targ_side, side_fir)

    for rms_step in range(1, 5):
        result_clipped = np.clip(result_mid, -1.0, 1.0)
        targ_loudest_RMS, *_ = apu.getLoudestMidSidePieces(result_clipped, targ_side, targ_pieces_quantity, targ_piece_size)
        *_, result = apu.calculateCoefficientAndAmplify(result_mid, result, targ_loudest_RMS, ref_loudest_RMS)

    sf.write(targetTrack.rsplit('.', 1)[0] + '_mastered.' + targetTrack.split('.')[-1], result, targ_rate)


