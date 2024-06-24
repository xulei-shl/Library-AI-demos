import os
from funasr import AutoModel
import lib
from lib import cfg, tool
import warnings

warnings.filterwarnings('ignore')

def convert_audio_to_text(audio_path, raw_transcript_file, timestamped_transcript_file):
    # 初始化模型
    model = AutoModel(model="paraformer-zh", model_revision="v2.0.4",
                      vad_model="fsmn-vad", vad_model_revision="v2.0.4",
                      punc_model="ct-punc-c", punc_model_revision="v2.0.4")

    original_audio_path = audio_path
    # 如果不是 wav 格式，创建一个临时的 wav 文件
    if not audio_path.lower().endswith('.wav'):
        wav_file = os.path.splitext(audio_path)[0] + '_temp.wav'
        params = ["-i", audio_path, "-vn", wav_file]
        rs = tool.runffmpeg(params)
        if rs != 'ok':
            print(f"预处理 {audio_path} 为 wav 时失败")
            return
        audio_path = wav_file

    # 转录音频
    res = model.generate(input=audio_path, return_raw_text=True, is_final=True,
                         sentence_timestamp=True, batch_size_s=100)

    # 原始转录文本
    # print(f"\n-------------------原始转录文本-----------------------\n")
    with open(raw_transcript_file, 'w', encoding='utf-8') as transcript_f:
        for item in res:
            # print(item['text'])
            transcript_f.write(item['text'] + '\n')

    # 写入带时间戳的结果到 md 文件
    with open(timestamped_transcript_file, 'w', encoding='utf-8') as f:
        for it in res[0]['sentence_info']:
            start_time = tool.ms_to_time_string(ms=it["start"])
            end_time = tool.ms_to_time_string(ms=it["end"])
            f.write(f"[{start_time} --> {end_time}] {it['text']}\n\n")

    print(f"\n-------------------转录结果保存-----------------------\n")
    print(f"已完成 {original_audio_path} 的转录\n\n原始转录文本保存在 {raw_transcript_file} \n\n时间戳文本保存在 {timestamped_transcript_file}")

    # 如果创建了临时 wav 文件，删除它
    if audio_path != original_audio_path:
        os.remove(audio_path)

def transcribe_audio_files_in_folder(folder_path):
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(('.wav', '.mp3', '.flac')):
                audio_path = os.path.join(root, file)
                raw_transcript_file = os.path.join(root, f"{os.path.splitext(file)[0]}_转录文本.md")
                timestamped_transcript_file = os.path.join(root, f"{os.path.splitext(file)[0]}_时间戳文本.md")
                convert_audio_to_text(audio_path, raw_transcript_file, timestamped_transcript_file)