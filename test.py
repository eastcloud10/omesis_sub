import librosa
print("114514")
file_path = "5s.mp4"
y, sr = librosa.load(file_path, sr = None, mono=True, offset = 0.0, duration = None)
print(len(y))