from pydub import AudioSegment, effects
from scipy.io import wavfile
from scipy import signal
import numpy as np

def equalizeFile(path: str, low_gain: float, mid_gain: float, high_gain: float):
    
    rate, data = wavfile.read(path) 
    # rate -  частота дискретизации (Гц),
    # data -  массив значений амплитуд звукового сигнала, представленных в виде целых чисел.
    
    freq, fft = signal.periodogram(data, rate)
    # freq - массив дискретных частот
    # fft  - массив соответствующих им амплитуд спектра.

    b, a = signal.butter(6, low, 'low', fs=rate)
    b, a = signal.butter(6, [low, high], 'bandpass', fs=rate)
    b, a = signal.butter(6, high, 'high', fs=rate)
    
    low_freq = signal.filtfilt(b, a, data)
   


    mid_freq = signal.filtfilt(b, a, data)
  
    

    high_freq = signal.filtfilt(b, a, data)
    
    output_signal = low_freq + mid_freq + high_freq

    output_signal = np.int16(output_signal / np.max(np.abs(output_signal)) * 32767)

def compressFile(path: str, threshold: float, ratio: float, attack=None, release=None):
    input_signal = AudioSegment.from_file(path, path.split('.')[-1])
    print("RMS level before compression: ", input_signal.rms)

    compressed_signal = input_signal.compress_dynamic_range(threshold=threshold, ratio=ratio, attack=attack, release=release)
    print("RMS level after compression: ", compressed_signal.rms)
    output_signal = compressed_signal

    output_path = output_path if output_path else path
    output_signal.export(output_path, format=output_path.split('.')[-1])

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

    output_path = output_path if output_path else path
    output_signal.export(output_path, format=output_path.split('.')[-1])

def byReference(path: str, ref_path: str):
    def getReferenceParams(ref_path: str) -> dict:
        params = {}
        input_signal = AudioSegment.from_file(ref_path, ref_path.split('.')[-1])
        params['dBFS'] = round(input_signal.dBFS, 1)
        print(params['dBFS'])
        return params

    def applyReferenceParams(path: str, params: dict):
        normalizeFile(path, dBFS=params['dBFS'])
    
    applyReferenceParams(path, getReferenceParams(ref_path))