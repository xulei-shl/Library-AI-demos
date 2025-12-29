from src.core.literature_fm import LiteratureFMPipeline

pipeline = LiteratureFMPipeline()
result = pipeline.generate_theme_shelf(
    theme_text="冬日夜深人静一杯咖啡一本书",  # 用户输入的情境主题
    use_vector=True,                          # 是否使用向量检索
    vector_weight=0.5,                        # 向量检索权重 (0-1)
    randomness=0.2,                           # 随机性因子 (0-1)，增加结果多样性
    min_confidence=0.8,                      # 最小置信度
    final_top_k=30,                           # 最终输出数量
    output_dir="runtime/outputs/theme_shelf", # 输出目录
    config_path="config/literature_fm_vector.yaml"  # 配置文件
)

print(result)