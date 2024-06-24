from pydub import AudioSegment
import os

def split_audio(file_path, segment_length_ms=600000):  # 600000 ms = 10 minutes
    # Load the audio file
    audio = AudioSegment.from_wav(file_path)
    
    # Get the base name of the file
    file_name = os.path.basename(file_path)
    file_name_without_ext = os.path.splitext(file_name)[0]
    
    # Calculate the number of segments
    num_segments = len(audio) // segment_length_ms
    
    # Split the audio into segments
    for i in range(num_segments):
        start_time = i * segment_length_ms
        end_time = start_time + segment_length_ms
        segment = audio[start_time:end_time]
        
        # Save the segment
        output_file_name = f"{file_name_without_ext}_segment_{i+1}.wav"
        output_file_path = os.path.join(os.path.dirname(file_path), output_file_name)
        segment.export(output_file_path, format="wav")
        print(f"Saved segment {i+1} to {output_file_path}")

if __name__ == "__main__":
    file_path = r"E:\scripts\AI-demo\video\共同书写移动植物的时间经验 植南门市部.wav"  # Replace with your file path
    split_audio(file_path)