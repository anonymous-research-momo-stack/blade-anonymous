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



class BinaryAnalyzer:
    def __init__(self, knowledge_json_path:str):

        knowledge_base = JSONKnowledgeBase(
            path=knowledge_json_path,
            vector_db=PgVector(
                table_name="json_documents",
                db_url=settings.KNOWLEDGE_DATABASE_URL,
                search_type=SearchType.hybrid  # Hybrid Search
            ),
        )

        self.agent = Agent(
            model=Claude(id=CLAUDE_MODEL_ID,
                         api_key=ANTHROPIC_API_KEY),
            tools=[DuckDuckGoTools()],
            show_tool_calls=True,
            knowledge=knowledge_base,
            search_knowledge=True,
            instructions=[
                "You are a binary analysis agent.",
                "Your task is to provide the information about the target binary, especially what may be it, which library may compile it, and what is the main function of it.",
                "If you are not familiar or not sure about the target binary, you can search the web for more information.",
                "You can also search the knowledge base for some information.",
            ],
            response_model=BinaryInformation,
        )

        self.agent.knowledge.load(recreate=False)


    def analyze(self, target_binary:TargetBinary):
        task_prompt = f"""the target binary is: {target_binary.binary_name},
            its size: {target_binary.file_size_kb} kb
            Please analyze this binary and provide information about what it might be, which library may have compiled it, and its main function.
"""


        response = self.agent.run(task_prompt)

        binary_info = response.content

        target_binary.information = binary_info


