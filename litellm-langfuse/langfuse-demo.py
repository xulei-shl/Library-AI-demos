import os 
import litellm
from litellm import completion
from langfuse import Langfuse

os.environ["LITELLM_PROXY_API_KEY"] = "anything"

litellm.api_base = "http://10.40.92.16:4000/v1"

langfuse_prompt = Langfuse().get_prompt('test')
print(langfuse_prompt.prompt)

response = litellm.completion(
    model="litellm_proxy/glm-4-flash",
    messages=[
        {"role": "system", "content": langfuse_prompt.prompt},
        {"role": "user", "content": "大模型应用一般需要有哪些工程基础组件？"}
    ],
)

print(response['choices'][0]['message']['content'])