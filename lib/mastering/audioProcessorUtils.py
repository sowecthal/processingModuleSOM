import numpy as np

def convertFromLeftRightToMidSide(data: np.ndarray) -> (np.ndarray, np.ndarray):
    data = np.copy(data)
    data[:, 0] += data[:, 1]
    data[:, 0] *= 0.5
    mid_data = np.copy(data[:, 0])
    data[:, 0] -= data[:, 1]
    side_data = np.copy(data[:, 0])
    return mid_data, side_data


def convertFromMidSideToLeftRight(mid_data: np.ndarray, side_data: np.ndarray) -> np.ndarray:
    return np.vstack((mid_data + side_data, mid_data - side_data)).T


def calculatePiecesParams(data: np.ndarray, rate: int, max_piece_duration=15) -> (int, int):
    data_size = data.shape[0]
    quantity = int(data_size / max_piece_duration) + 1
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
    average_RMS = getAverageRMS(RMSes)

    loudest_indexes = getLoudestIndexes(RMSes, average_RMS)
    loudest_average_RMS = getRMS(RMSes[loudest_indexes])

    mid_loudest_pieces = mid_pieces[loudest_indexes]
    side_loudest_pieces = side_pieces[loudest_indexes]

    return loudest_average_RMS, mid_loudest_pieces, side_loudest_pieces

    
    


