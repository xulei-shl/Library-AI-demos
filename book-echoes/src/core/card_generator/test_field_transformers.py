"""
字段转换器测试脚本
用于验证字段转换器的功能是否正常
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, project_root)

from src.core.card_generator.field_transformers import (
    DirectTransformer,
    FirstAuthorTransformer,
    MainTitleOnlyTransformer,
    FullTitleTransformer,
    FieldTransformerFactory
)


def test_direct_transformer():
    """测试直接转换器"""
    print("=" * 60)
    print("测试1: DirectTransformer (直接转换器)")
    print("=" * 60)
    
    transformer = DirectTransformer()
    
    # 测试用例1: 正常值
    result = transformer.transform("张三")
    print(f"输入: '张三' -> 输出: '{result}'")
    assert result == "张三", "测试失败"
    
    # 测试用例2: 空值
    result = transformer.transform(None, default="默认值")
    print(f"输入: None (default='默认值') -> 输出: '{result}'")
    assert result == "默认值", "测试失败"
    
    print("✓ DirectTransformer 测试通过\n")


def test_first_author_transformer():
    """测试第一作者转换器"""
    print("=" * 60)
    print("测试2: FirstAuthorTransformer (第一作者转换器)")
    print("=" * 60)
    
    transformer = FirstAuthorTransformer()
    
    # 测试用例1: 单个作者
    result = transformer.transform("张三")
    print(f"输入: '张三' -> 输出: '{result}'")
    assert result == "张三", "测试失败"
    
    # 测试用例2: 多个作者(默认分隔符)
    result = transformer.transform("张三 / 李四 / 王五")
    print(f"输入: '张三 / 李四 / 王五' -> 输出: '{result}'")
    assert result == "张三 等", "测试失败"
    
    # 测试用例3: 多个作者(自定义分隔符和后缀)
    result = transformer.transform("张三、李四、王五", separator="、", suffix="等著")
    print(f"输入: '张三、李四、王五' (separator='、', suffix='等著') -> 输出: '{result}'")
    assert result == "张三等著", "测试失败"
    
    # 测试用例4: 空值
    result = transformer.transform(None, default="佚名")
    print(f"输入: None (default='佚名') -> 输出: '{result}'")
    assert result == "佚名", "测试失败"
    
    print("✓ FirstAuthorTransformer 测试通过\n")


def test_main_title_only_transformer():
    """测试主标题转换器"""
    print("=" * 60)
    print("测试3: MainTitleOnlyTransformer (主标题转换器)")
    print("=" * 60)
    
    transformer = MainTitleOnlyTransformer()
    
    # 测试用例1: 正常标题
    result = transformer.transform("人类简史")
    print(f"输入: '人类简史' -> 输出: '{result}'")
    assert result == "人类简史", "测试失败"
    
    # 测试用例2: 空值
    result = transformer.transform(None, default="未知书名")
    print(f"输入: None (default='未知书名') -> 输出: '{result}'")
    assert result == "未知书名", "测试失败"
    
    print("✓ MainTitleOnlyTransformer 测试通过\n")


def test_full_title_transformer():
    """测试完整标题转换器"""
    print("=" * 60)
    print("测试4: FullTitleTransformer (完整标题转换器)")
    print("=" * 60)
    
    transformer = FullTitleTransformer()
    
    # 测试用例1: 有副标题
    result = transformer.transform("人类简史", subtitle="从动物到上帝")
    print(f"输入: 主='人类简史', 副='从动物到上帝' -> 输出: '{result}'")
    assert result == "人类简史 : 从动物到上帝", "测试失败"
    
    # 测试用例2: 无副标题
    result = transformer.transform("人类简史", subtitle=None)
    print(f"输入: 主='人类简史', 副=None -> 输出: '{result}'")
    assert result == "人类简史", "测试失败"
    
    # 测试用例3: 自定义分隔符
    result = transformer.transform("人类简史", subtitle="从动物到上帝", separator="——")
    print(f"输入: 主='人类简史', 副='从动物到上帝' (separator='——') -> 输出: '{result}'")
    assert result == "人类简史——从动物到上帝", "测试失败"
    
    # 测试用例4: 空值
    result = transformer.transform(None, default="未知书名")
    print(f"输入: None (default='未知书名') -> 输出: '{result}'")
    assert result == "未知书名", "测试失败"
    
    print("✓ FullTitleTransformer 测试通过\n")


def test_factory():
    """测试工厂类"""
    print("=" * 60)
    print("测试5: FieldTransformerFactory (工厂类)")
    print("=" * 60)
    
    # 测试用例1: 创建direct转换器
    transformer = FieldTransformerFactory.create('direct')
    print(f"创建 'direct' 转换器: {type(transformer).__name__}")
    assert isinstance(transformer, DirectTransformer), "测试失败"
    
    # 测试用例2: 创建first_author转换器
    transformer = FieldTransformerFactory.create('first_author')
    print(f"创建 'first_author' 转换器: {type(transformer).__name__}")
    assert isinstance(transformer, FirstAuthorTransformer), "测试失败"
    
    # 测试用例3: 创建main_title_only转换器
    transformer = FieldTransformerFactory.create('main_title_only')
    print(f"创建 'main_title_only' 转换器: {type(transformer).__name__}")
    assert isinstance(transformer, MainTitleOnlyTransformer), "测试失败"
    
    # 测试用例4: 创建full_title转换器
    transformer = FieldTransformerFactory.create('full_title')
    print(f"创建 'full_title' 转换器: {type(transformer).__name__}")
    assert isinstance(transformer, FullTitleTransformer), "测试失败"
    
    # 测试用例5: 创建不存在的转换器
    try:
        transformer = FieldTransformerFactory.create('invalid_type')
        print("错误: 应该抛出异常")
        assert False, "测试失败"
    except ValueError as e:
        print(f"创建 'invalid_type' 转换器: 正确抛出异常 - {e}")
    
    print("✓ FieldTransformerFactory 测试通过\n")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("字段转换器测试")
    print("=" * 60 + "\n")
    
    try:
        test_direct_transformer()
        test_first_author_transformer()
        test_main_title_only_transformer()
        test_full_title_transformer()
        test_factory()
        
        print("=" * 60)
        print("✓ 所有测试通过!")
        print("=" * 60)
        return 0
    
    except AssertionError as e:
        print("\n" + "=" * 60)
        print(f"✗ 测试失败: {e}")
        print("=" * 60)
        return 1
    
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"✗ 测试异常: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
