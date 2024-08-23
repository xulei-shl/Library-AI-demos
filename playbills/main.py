from pics_ocr import process_images
from tools.baidu_token import load_access_token
from tools.logs import setup_logger
from festivals_metadata_extractor import festivals_metadata
from shows_list_extractor import structured_shows_list
from shows_list_processor import pre_shows_list
from shows_list_reprocessor import replace_texts
from casts_list_extractor import process_casts_list
from casts_list_optimizer import optimize_casts

# 第一步 OCR，OCR结果LLM整理

# 配置图片文件夹地址
image_folder = r'E:\scripts\jiemudan\2'

# 配置 OCR URL
ocr_url = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate"

# 获取 access_token
access_token = load_access_token()

# 设置日志记录器
logger = setup_logger(r'E:\scripts\jiemudan\logs')

# 1 调用 OCR 处理函数
# process_images(image_folder, ocr_url, access_token, logger)

# # 2 集合演出元数据提取
# festivals_metadata(image_folder, logger)

# # 3 演出节目清单信息提取
# # 3.1 纯节目清单预处理
# pre_shows_list(image_folder, logger)

# # 3.2 节目清单结构化提取
# structured_shows_list(image_folder, logger)


# 4 演职人员清单信息提取
#process_casts_list(image_folder, logger)

# 5 3.1节目清单中演职人员castDescription结构化
optimize_casts(image_folder, logger)

# Excel 数据处理
# replace_texts(image_folder)



