import numpy as np
from resampy import resample

def checkSampleRate(data: np.ndarray, sample_rate: int, required_sample_rate: int) -> (np.ndarray, int):
    if sample_rate != required_sample_rate:
        data = resample(data, sample_rate, required_sample_rate, axis=0)
    return data, required_sample_rate


def checkLength(data: np.ndarray, max_length: int, min_length: int) -> None:
    length = data.shape[0]
    if length > max_length:
        raise ValueError
    elif length < min_length:
        raise ValueError


def checkChannels(data: np.ndarray) -> np.ndarray:
    if data.shape[1] == 1:
        data = np.repeat(data, repeats=2, axis=1)
    elif not data.shape[1] == 2:
        raise ValueError("Not stereo")
    return data


def check(data: np.ndarray, sample_rate: int, max_length: float = 15 * 60, fft_size: int = 4096, internal_sample_rate: int = 44100,) -> (np.ndarray, int):
    checkLength(data, max_length * sample_rate, fft_size * sample_rate // internal_sample_rate)
    data = checkChannels(data)
    data, sample_rate = checkSampleRate(data, sample_rate, internal_sample_rate)

    return data, sample_rate


def checkEquality(target: np.ndarray, reference: np.ndarray) -> None:
    if target.shape == reference.shape and np.allclose(target, reference):
        raise ValueError