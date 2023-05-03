import numpy as np
from resampy import resample

def __check_sample_rate(
    array: np.ndarray,
    sample_rate: int,
    required_sample_rate: int,
) -> (np.ndarray, int):
    if sample_rate != required_sample_rate:
        array = resample(array, sample_rate, required_sample_rate, axis=0)
    return array, required_sample_rate


def __check_length(
    data: np.ndarray,
    max_length: int,
    min_length: int,

) -> None:
    length = data.shape[0]
    if length > max_length:
        raise ValueError
    elif length < min_length:
        raise ValueError


def __check_channels(data: np.ndarray) -> np.ndarray:
    if data.shape[1] == 1:
        data = np.repeat(data, repeats=2, axis=1)
    elif not data.shape[1] == 2:
        raise ValueError("Not stereo")
    return data


def __check_clipping_limiting(
    data: np.ndarray,
    clipping_samples_threshold: int,
    limited_samples_threshold: int,
) -> None:
    max_value = np.abs(data).max()
    max_count = np.count_nonzero(
        np.logical_or(np.isclose(data, max_value), np.isclose(array, -max_value))
    )
    if max_count > clipping_samples_threshold:
        if np.isclose(max_value, 1.0):
            print("Warning np.isclose(max_value, 1.0)")
        elif max_count > limited_samples_threshold:
            print("Warning max_count > limited_samples_threshold")


def check(data: np.ndarray, sample_rate: int, max_length: float = 15 * 60, fft_size: int = 4096, internal_sample_rate: int = 44100,) -> (np.ndarray, int):
    __check_length(
        data,
        max_length * sample_rate,
        fft_size * sample_rate // internal_sample_rate,
    )

    data = __check_channels(data)
    data, sample_rate = __check_sample_rate(data, sample_rate, internal_sample_rate)

    return data, sample_rate


def check_equality(target: np.ndarray, reference: np.ndarray) -> None:
    if target.shape == reference.shape and np.allclose(target, reference):
        raise ValueError