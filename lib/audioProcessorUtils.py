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


