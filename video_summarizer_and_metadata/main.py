import os
from video2audio import convert_videos_in_folder
from audio2text import transcribe_audio_files_in_folder
from transcript_correction import optimize_transcripts_in_folder
from insights import get_insights_in_folder
from xhs import social_media_writer
from dotenv import load_dotenv
from datetime import date


load_dotenv()

llm_configs = {
    "glm": {
        "temperature": 0,
        "model_name": os.getenv("GLM_MODEL_NAME"),
        "api_key": os.getenv("GLM_API_KEY"),
    },
    "glmweb": {
        "temperature": 0,
        "model_name": os.getenv("WEB_MODEL_NAME"),
        "api_base": os.getenv("WEB_API_BASE"),
        "api_key": os.getenv("WEB_API_KEY"),
    }    
}

def process_folder(folder_path):
    print(f"\n-------------------开始处理视频文件...----------------------\n")
    convert_videos_in_folder(folder_path)
    print(f"\n-------------------视频转音频完成----------------------\n")

    print(f"\n-------------------开始转录音频文件...----------------------\n")
    transcribe_audio_files_in_folder(folder_path)
    print(f"\n-------------------音频转文本完成----------------------\n")

    print(f"\n-------------------开始优化转录文本...----------------------\n")
    optimize_transcripts_in_folder(folder_path, llm_configs)
    print(f"\n-------------------转录文本优化完成----------------------\n")

    print(f"\n-------------------开始文本总结...----------------------\n")
    get_insights_in_folder(folder_path, llm_configs)
    print(f"\n-------------------文本总结完成----------------------\n")

    print(f"\n-------------------开始小红书文案...----------------------\n")
    social_media_writer(folder_path, llm_configs)
    print(f"\n-------------------文案撰写完成----------------------\n")

if __name__ == '__main__':
    today = date.today()
    folder_name = today.strftime("%Y-%m-%d") 
    folder_path = os.path.join(r"E:\scripts\AI-demo\video", folder_name)
    if os.path.isdir(folder_path):
        process_folder(folder_path)
    else:
        print("无效的文件夹路径")