import moviepy.editor as edr
import os

def export_audio_from_video(src_file, dst_file):
    """
    提取视频中的音频，并进行处理
    :param src_file: 输入视频文件路径
    :param dst_file: 输出音频文件路径
    :return:
    """
    # 1. 读取目标文件
    video = edr.VideoFileClip(filename=src_file)

    # 2. 取出其中的音频数据结构并直接保存为指定格式
    video.audio.write_audiofile(filename=dst_file, fps=16000, nbytes=2, codec='pcm_s16le')

    video.close()  # 关闭视频文件，释放资源

    print(f"\n-----------------音频转换完成: {dst_file}-----------------------\n")

def convert_videos_in_folder(folder_path):
    """
    转换文件夹及其子文件夹中的所有视频文件为音频
    """
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(('.ts', '.mp4', '.avi', '.mov', '.mkv', '.flv')):  # 支持多种视频格式
                video_path = os.path.join(root, file)
                audio_path = os.path.splitext(video_path)[0] + '.wav'
                export_audio_from_video(video_path, audio_path)

# if __name__ == '__main__':
#     folder_path = input("请输入要处理的文件夹路径: ")
#     convert_videos_in_folder(folder_path)