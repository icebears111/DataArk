"""
项目配置文件。

pydantic-settings 会自动从 .env 文件或环境变量读取配置。
如果你不知道怎么填，复制 .env.example 为 .env 就行：
  cp .env.example .env
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ----- 应用基础配置 -----
    APP_NAME: str = "DataArk"
    DEBUG: bool = True

    # ----- JWT 密钥（生产环境务必改掉！）-----
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 小时过期

    # ----- 数据库 -----
    DATABASE_URL: str = "sqlite:///./dataark.db"

    # ----- LLM 配置 -----
    # 用什么方式访问 LLM？可选：openai, ollama
    # openai = 通过 OpenAI 兼容 API（阿里云百炼、DeepSeek、GLM 等）
    # ollama = 通过本地 Ollama
    LLM_PROVIDER: str = "openai"

    # 方式1: OpenAI 兼容 API
    # Qwen DashScope: base=https://dashscope.aliyuncs.com/compatible-mode/v1
    # DeepSeek:        base=https://api.deepseek.com
    # GLM:             base=https://open.bigmodel.cn/api/paas/v4
    LLM_API_KEY: str = ""
    LLM_API_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    LLM_MODEL: str = "qwen-plus"

    # 方式2: 本地模型（通过 Ollama）
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"

    # ----- Embedding 模型（用于文档向量化）-----
    # Qwen DashScope: text-embedding-v2 或 text-embedding-v3
    # OpenAI: text-embedding-3-small
    # 本地: BAAI/bge-small-zh-v1.5
    EMBEDDING_MODEL: str = "text-embedding-v2"
    # Embedding 专用 API 地址（通常和 LLM 相同）
    EMBEDDING_API_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # ----- 向量数据库存储路径 -----
    CHROMA_PERSIST_DIR: str = "./chroma_data"

    class Config:
        env_file = ".env"


settings = Settings()
