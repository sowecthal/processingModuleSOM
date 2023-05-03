import numpy as np
from scipy import signal, interpolate
import statsmodels.api as sm

def convertFromLeftRightToMidSide(data: np.ndarray) -> (np.ndarray, np.ndarray):
    data = np.copy(data)
    data[:, 0] += data[:, 1]
    data[:, 0] *= 0.5
    mid_data = np.copy(data[:, 0])
    data[:, 0] -= data[:, 1]
    side_data = np.copy(data[:, 0])
    print(mid_data, side_data)
    print(mid_data.shape, side_data.shape)
    return mid_data, side_data


def convertFromMidSideToLeftRight(mid_data: np.ndarray, side_data: np.ndarray) -> np.ndarray:
    return np.vstack((mid_data + side_data, mid_data - side_data)).T


def calculatePiecesParams(data: np.ndarray, rate: int, max_piece_duration=15) -> (int, int):
    data_size = data.shape[0]
    quantity = int(data_size / (max_piece_duration*rate)) + 1
    piece_size = int(data_size / quantity)
    return quantity, piece_size


def divideIntoPieces(data: np.ndarray, quantity: int, piece_size: int) -> np.ndarray:
    return data[: piece_size * quantity].reshape(-1, piece_size)


def getRMSes(data: np.ndarray) -> np.ndarray:
    piece_size = data.shape[1]
    multiplicand = data[:, None, :]
    multiplier = data[..., None]
    return np.sqrt(np.squeeze(multiplicand @ multiplier, axis=(1, 2)) / piece_size)


def getRMS(data: np.ndarray) -> float:
    return np.sqrt(data @ data / data.shape[0])


def getLoudestIndexes(RMSes: np.ndarray, average: float) -> np.ndarray:
    return np.where(RMSes >= average)


def getLoudestMidSidePieces(mid: np.ndarray, side: np.ndarray, quantity: int, piece_size: int) -> (np.ndarray, np.ndarray):
    mid_pieces = divideIntoPieces(mid, quantity, piece_size)
    side_pieces = divideIntoPieces(side, quantity, piece_size)

    RMSes = getRMSes(mid_pieces)
    average_RMS = getRMS(RMSes)

    loudest_indexes = getLoudestIndexes(RMSes, average_RMS)
    loudest_average_RMS = getRMS(RMSes[loudest_indexes]) #match_rms

    mid_loudest_pieces = mid_pieces[loudest_indexes]
    side_loudest_pieces = side_pieces[loudest_indexes]

    return loudest_average_RMS, mid_loudest_pieces, side_loudest_pieces


def calculateCoefficientAndAmplify(data_mid: np.ndarray, data_side: np.ndarray, target_main_match_rms: float, reference_match_rms: float) -> (float, np.ndarray, np.ndarray):
    rms_coefficient = reference_match_rms / target_main_match_rms

    data_mid = data_mid * rms_coefficient
    data_side = data_side * rms_coefficient

    return rms_coefficient, data_mid, data_side


def smoothLowess(fft_data: np.ndarray, frac = 0.0375, it = 0, delta = 0.001) -> np.ndarray:
    lowess_smooth = sm.nonparametric.lowess(fft_data, np.linspace(0, 1, len(fft_data)), frac=frac, it=it, delta=delta)[:, 1]

    return lowess_smooth


def averageFFT(loudest_pieces: np.ndarray) -> np.ndarray:

    *_, specs = signal.stft(loudest_pieces, fs=44100, window="boxcar", nperseg=4096, noverlap=0, boundary=None, padded=False)
    fft_average = np.abs(specs).mean((0, 2))
    
    return fft_average


def smoothExponentially(matching_fft: np.ndarray, lin_log_oversampling = 4) -> np.ndarray:
    grid_linear = (44100 * 0.5 * np.linspace(0, 1, 4096 // 2 + 1))

    grid_logarithmic = (44100 * 0.5 * np.logspace(np.log10(4 / 4096), 0, (4096 // 2) * lin_log_oversampling + 1))

    interpolator = interpolate.interp1d(grid_linear, matching_fft, "cubic")
    matching_fft_log = interpolator(grid_logarithmic)

    matching_fft_log_filtered = smoothLowess(matching_fft_log)

    interpolator = interpolate.interp1d(grid_logarithmic, matching_fft_log_filtered, "cubic", fill_value="extrapolate")
    
    matching_fft_filtered = interpolator(grid_linear)

    matching_fft_filtered[0] = 0
    matching_fft_filtered[1] = matching_fft[1]

    return matching_fft_filtered


def getFIR(targ_loudest_pieces: np.ndarray, ref_loudest_pieces: np.ndarray) -> np.ndarray:

    targ_average_fft = averageFFT(targ_loudest_pieces)
    ref_average_fft = averageFFT(ref_loudest_pieces)

    matching_fft = ref_average_fft / targ_average_fft

    matching_fft_filtered = smoothExponentially(matching_fft)

    fir = np.fft.irfft(matching_fft_filtered)
    fir = np.fft.ifftshift(fir) * signal.windows.hann(len(fir))

    return fir


def convolve(targ_mid: np.ndarray, mid_fir: np.ndarray, targ_side: np.ndarray, side_fir: np.ndarray) -> (np.ndarray, np.ndarray):
    result_mid = signal.fftconvolve(targ_mid, mid_fir, "same")
    result_side = signal.fftconvolve(targ_side, side_fir, "same")

    result = convertFromMidSideToLeftRight(result_mid, result_side)

    return result, result_mid


