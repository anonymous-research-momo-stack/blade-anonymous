from agno.agent import Agent
from agno.knowledge.json import JSONKnowledgeBase
from agno.models.anthropic import Claude
from agno.vectordb.pgvector import PgVector
from agno.vectordb.search import SearchType
from environs import Env

from app.config import settings
from app.interface import TargetBinary, BinaryInformation

env = Env()
env.read_env()
from agno.tools.duckduckgo import DuckDuckGoTools

# TODO 移动到环境变量中
ANTHROPIC_API_KEY = env.str("ANTHROPIC_API_KEY")
CLAUDE_MODEL_ID = "claude-sonnet-4-20250514"


class BinaryInformationFinder:
    def __init__(self,
                 knowledge_json_path: str = None,
                 enable_web_search: bool = True,
                 enable_knowledge_base: bool = True):

        # 构建工具列表
        tools = []
        if enable_web_search:
            tools.append(DuckDuckGoTools())

        # 构建知识库
        knowledge = None
        if enable_knowledge_base:
            if knowledge_json_path is None:
                raise ValueError("knowledge_json_path is required when enable_knowledge_base=True")

            knowledge = JSONKnowledgeBase(
                path=knowledge_json_path,
                vector_db=PgVector(
                    table_name="json_documents",
                    db_url=settings.KNOWLEDGE_DATABASE_URL,
                    search_type=SearchType.hybrid  # Hybrid Search
                ),
            )

        # 构建instructions
        instructions = [
            "You are an expert binary analysis assistant specialized in identifying and analyzing executable files, libraries, and binary components.",

            "Your primary task is to help identify unknown binary files by providing comprehensive information including what the binary is, its main functionality, which software package or library it belongs to, common use cases, and any security considerations.",

            "When analyzing a binary, consider file naming patterns, typical file sizes for known binary types, common libraries and frameworks, and platform-specific characteristics.",
        ]

        # 根据开关状态添加搜索相关指令
        if enable_knowledge_base or enable_web_search:
            instructions.append("If you're not certain about a binary identification:")

        if enable_web_search:
            instructions.append("- Search the web for additional information about the binary name and characteristics")

        if enable_knowledge_base:
            instructions.append("- Consult the knowledge base for similar binaries and patterns")

        instructions.extend([
            "- Provide your best assessment based on available information",
            "- Clearly indicate your confidence level in the identification",
            "",
            "Always structure your response to be practical and actionable for binary analysis workflows.",
            "Focus on providing comprehensive information in the description field that would be valuable for security analysis, reverse engineering, or system administration."
        ])

        self.agent = Agent(
            model=Claude(id=CLAUDE_MODEL_ID,
                         api_key=ANTHROPIC_API_KEY),
            tools=tools,
            show_tool_calls=True,
            knowledge=knowledge,
            search_knowledge=enable_knowledge_base,
            instructions=instructions,
            response_model=BinaryInformation,
        )

        # 只有在知识库存在时才加载
        if knowledge is not None:
            self.agent.knowledge.load(recreate=False)

    def find_for(self, target_binary: TargetBinary):
        task_prompt = f"""Please analyze this binary file and provide detailed identification information:

Binary Details:
- Name: {target_binary.binary_name}
- Size: {target_binary.file_size_kb} KB

Please provide comprehensive analysis including:
- What this binary is (type, purpose, category)
- Main functionality and purpose
- Which software package, framework, or library it belongs to
- Common use cases and contexts where it appears
- Any security considerations or notable characteristics
- Your confidence level in this identification

If the binary appears to be compiled from or related to a specific library or framework, please also identify that source library."""

        response = self.agent.run(task_prompt)

        binary_info = response.content

        target_binary.information = binary_info