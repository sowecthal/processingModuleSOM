from pydub import AudioSegment, effects

def equalizeFile(path: str, low: int, mid: int, high: int):
    pass

def compressFile(path: str, threshold: int, ratio: int):
    pass

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
