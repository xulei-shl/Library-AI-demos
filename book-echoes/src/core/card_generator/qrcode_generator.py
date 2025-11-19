"""
二维码生成器模块
负责将索书号转换为二维码图片
"""

from typing import Dict, Tuple
import qrcode
from PIL import Image
from src.utils.logger import get_logger

logger = get_logger(__name__)


class QRCodeGenerator:
    """二维码生成器类"""

    def __init__(self, config: Dict):
        """
        初始化二维码生成器

        Args:
            config: 配置字典
        """
        self.config = config.get('qrcode', {})
        self.url_template = self.config.get(
            'url_template',
            'https://vufind.library.sh.cn/Search/Results?searchtype=vague&lookfor={call_number}&type=CallNumber'
        )
        self.encoding_rules = self.config.get('url_encoding', {})
        self.box_size = self.config.get('box_size', 10)
        self.border = self.config.get('border', 4)
        self.error_correction = self.config.get('error_correction', 'H')

    def generate_qrcode(
        self, call_number: str, output_path: str
    ) -> Tuple[bool, str]:
        """
        生成二维码

        Args:
            call_number: 索书号
            output_path: 输出路径

        Returns:
            Tuple[bool, str]: (是否成功, 保存路径)
        """
        if not call_number or not call_number.strip():
            logger.error("索书号为空，无法生成二维码")
            return False, ""

        try:
            # 构建检索URL
            search_url = self.build_search_url(call_number)

            logger.debug(f"生成二维码，索书号：{call_number}，URL：{search_url}")

            # 创建二维码
            qr_image = self.create_transparent_qrcode(search_url)

            # 保存二维码
            qr_image.save(output_path, format='PNG')

            logger.debug(f"二维码生成成功：{output_path}")
            return True, output_path

        except Exception as e:
            logger.error(f"二维码生成失败，索书号：{call_number}，错误：{e}")
            return False, ""

    def build_search_url(self, call_number: str) -> str:
        """
        构建检索URL

        Args:
            call_number: 索书号

        Returns:
            str: 完整的检索URL
        """
        # 对索书号进行URL编码
        encoded_call_number = self.encode_call_number(call_number)

        # 填充URL模板
        search_url = self.url_template.format(call_number=encoded_call_number)

        return search_url

    def encode_call_number(self, call_number: str) -> str:
        """
        对索书号进行URL编码

        Args:
            call_number: 原始索书号

        Returns:
            str: 编码后的索书号
        """
        encoded = call_number

        # 应用编码规则
        for char, code in self.encoding_rules.items():
            encoded = encoded.replace(char, code)

        return encoded

    def create_transparent_qrcode(self, data: str) -> Image.Image:
        """
        创建透明背景的二维码图片

        Args:
            data: 二维码数据

        Returns:
            Image.Image: PIL图片对象
        """
        # 错误纠正级别映射
        error_correction_map = {
            'L': qrcode.constants.ERROR_CORRECT_L,
            'M': qrcode.constants.ERROR_CORRECT_M,
            'Q': qrcode.constants.ERROR_CORRECT_Q,
            'H': qrcode.constants.ERROR_CORRECT_H,
        }

        error_correction = error_correction_map.get(
            self.error_correction,
            qrcode.constants.ERROR_CORRECT_H
        )

        # 创建二维码对象
        qr = qrcode.QRCode(
            version=None,  # 自动选择版本
            error_correction=error_correction,
            box_size=self.box_size,
            border=self.border,
        )

        # 添加数据
        qr.add_data(data)
        qr.make(fit=True)

        # 生成图片（黑白二维码）
        img = qr.make_image(fill_color="black", back_color="white")

        # 转换为RGBA模式以支持透明背景
        img = img.convert("RGBA")
        datas = img.getdata()

        new_data = []
        for item in datas:
            # 将白色背景变为透明
            if item[0] == 255 and item[1] == 255 and item[2] == 255:
                new_data.append((255, 255, 255, 0))  # 透明
            else:
                new_data.append(item)

        img.putdata(new_data)

        return img
