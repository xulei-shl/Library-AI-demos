from langfuse_llm import get_llm_response
from utils.response_parser import parse_llm_response
from utils.prompt import LLMConfig, ConfigSource, PromptType

def analyze_query(
    user_query: str, 
    model_name: str = None,
    base_url: str = None,
    api_key: str = None,
    temperature: float = None,
    prompt_source: ConfigSource = ConfigSource.LANGFUSE,
    config_source: ConfigSource = ConfigSource.LANGFUSE,
    prompt_name: str = None,
    prompt_type: PromptType = None,
    system_prompt: str = None,
    trace_name: str = None,
    trace_tags: list = None,
    trace_metadata: dict = None,
    prompt_label: int = None,
) -> str:
    """
    使用 LLM 对用户的查询问题进行分析与扩展

    参数:
        user_query (str): 用户输入的查询文本，必需参数
        model_name (str, optional): LLM模型名称。当 config_source=ConfigSource.DIRECT 时必需
        base_url (str, optional): API基础URL。当 config_source=ConfigSource.DIRECT 时必需
        api_key (str, optional): API密钥。当 config_source=ConfigSource.DIRECT 时必需
        temperature (float, optional): 生成文本的随机性，范围0-1。当 config_source=ConfigSource.DIRECT 时可选，默认0.7

        prompt_source (ConfigSource, optional): 提示词来源，可选值：ConfigSource.LANGFUSE/ConfigSource.DIRECT，默认LANGFUSE
        config_source (ConfigSource, optional): 配置来源，可选值：ConfigSource.LANGFUSE/ConfigSource.DIRECT，默认LANGFUSE
        prompt_name (str, optional): Langfuse中的提示词名称。当 prompt_source=ConfigSource.LANGFUSE 时必需
        prompt_type (PromptType, optional): 提示词类型，可选值：PromptType.SYSTEM/PromptType.USER。当使用Langfuse提示词时必需
        prompt_label (int, optional): Langfuse提示词版本。当 prompt_source=ConfigSource.LANGFUSE 时可选

    返回:
        str: 分析后的结果文本
    """
    try:
        # 构建直接配置（如果提供）
        config = None
        if all([model_name, base_url, api_key]):
            config = LLMConfig(
                model_name=model_name,
                base_url=base_url,
                api_key=api_key,
                temperature=temperature or 0.7
            )
            # 如果提供了完整配置，默认使用直接配置源
            config_source = ConfigSource.DIRECT
        
        # 如果提供了system_prompt，默认使用直接提示词源
        if system_prompt:
            prompt_source = ConfigSource.DIRECT

        # 设置默认值
        if trace_name is None:
            trace_name = "查询分析"
        if trace_tags is None:
            trace_tags = ["查询分析"]
        if trace_metadata is None:
            trace_metadata = {"project": "cnki"}

        # 调用 LLM
        response = get_llm_response(
            user_prompt=user_query,
            system_prompt=system_prompt,
            prompt_name=prompt_name,
            prompt_type=prompt_type,
            config=config,
            prompt_source=prompt_source,
            config_source=config_source,
            trace_name=trace_name,
            trace_tags=trace_tags,
            trace_metadata=trace_metadata,
            prompt_label=prompt_label
        )
        
        if response and response.choices:
            reasoning = getattr(response.choices[0].message, 'reasoning_content', '')
            answer = response.choices[0].message.content
            return "\n".join([
                "## 思考过程\n\n",
                reasoning,
                "## 回答\n\n",
                answer
            ]) if reasoning else answer
        return user_query
        
    except Exception as e:
        print(f"查询改写失败: {str(e)}")
        return user_query