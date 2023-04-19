from pydub import AudioSegment, effects
from scipy.io import wavfile
from scipy import signal
import numpy as np

def equalizeFile(path: str, low_gain: float, mid_gain: float, high_gain: float):
    audio = AudioSegment.from_file(path, format=path.split('.')[-1])
    rate = audio.frame_rate
    data = np.array(audio.get_array_of_samples())
    
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
    output_signal = np.int16(output_signal / np.max(np.abs(output_signal)) * 32767)
    output_signal = AudioSegment(output_signal.tobytes(), frame_rate=rate, sample_width=4, channels=1)

    output_signal.export(path, format=path.split('.')[-1])

def compressFile(path: str, threshold: float, ratio: float, attack=5.0, release=50.0):
    input_signal = AudioSegment.from_file(path, path.split('.')[-1])
    print("RMS level before compression: ", input_signal.rms)

    output_signal = input_signal.compress_dynamic_range(threshold=threshold, ratio=ratio, attack=attack, release=release)
    print("RMS level after compression: ", output_signal.rms)
    
    output_signal.export(path, format=path.split('.')[-1])

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
