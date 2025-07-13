import os
import traceback
from collections import Counter
from typing import List, Dict
from loguru import logger

from agno.agent import Agent
from agno.knowledge.json import JSONKnowledgeBase
from agno.run.response import RunResponse
from agno.vectordb.pgvector import PgVector
from agno.vectordb.search import SearchType

from app.config import settings
from app.interface import TargetBinary, Library
from app.tpl_detection.agent_analysis.response_models import IndividualValidationResults, RedundancyAnalysisResult, \
    RedundancyAnalysisResults
from app.tpl_detection.agent_analysis.model_factory import create_model
from agno.tools.duckduckgo import DuckDuckGoTools


class LibraryValidator:
    """
    专家级库验证器：智能二进制组成分析
    """

    def __init__(self,
                 knowledge_json_path: str = None,
                 enable_web_search: bool = True,
                 enable_knowledge_base: bool = False,
                 enable_db_verification: bool = True,
                 debug_mode: bool = False):

        self.enable_db_verification = enable_db_verification
        self.debug_mode = debug_mode

        # 设置调试环境变量
        if debug_mode:
            os.environ["AGNO_DEBUG"] = "true"

        # Build tools list
        tools = []
        if enable_web_search:
            tools.append(DuckDuckGoTools())

        # Build knowledge base
        knowledge = None
        if enable_knowledge_base and knowledge_json_path:
            knowledge = JSONKnowledgeBase(
                path=knowledge_json_path,
                vector_db=PgVector(
                    table_name="library_validation_documents",
                    db_url=settings.KNOWLEDGE_DATABASE_URL,
                    search_type=SearchType.hybrid
                ),
            )

        # 专家级验证指令
        expert_instructions = [
            "You are a senior binary composition analysis expert with deep knowledge of software architecture and library ecosystems.",

            "CORE MISSION: Identify libraries whose SOURCE CODE is compiled into binaries",
            "NOT: Libraries that this binary calls or uses as dependencies",
            "NOT: Libraries that share similar function names or terminology",

            "CRITICAL DISTINCTION:",
            "✓ 'Library code compiled into binary' - actual source code inclusion",
            "✗ 'Binary calls library functions' - external API usage, NOT code inclusion",
            "✗ 'Similar function names detected' - shared terminology, NOT code inclusion",

            "CORE EXPERTISE:",
            "- Binary composition analysis: identifying SOURCE CODE actually compiled into binaries",
            "- Software architecture patterns: understanding how libraries are integrated",
            "- Library ecosystem knowledge: recognizing relationships between libraries",
            "- Evidence evaluation: distinguishing code inclusion from API usage",

            "ANALYSIS PHILOSOPHY:",
            "- Think like a forensic expert: distinguish actual code presence from false signals",
            "- Use domain knowledge: understand how software systems are actually built",
            "- Be systematic: consider multiple dimensions before making decisions",
            "- Be decisive: provide clear, well-reasoned conclusions based on evidence",

            "PROFESSIONAL REASONING STYLE:",
            "- Multi-dimensional analysis covering all relevant aspects",
            "- Clear logical progression from evidence to conclusion",
            "- Professional terminology and technical accuracy",
            "- Confident decisions backed by solid reasoning",

            "QUALITY STANDARDS:",
            "- Every conclusion must be supported by compelling evidence",
            "- Reasoning must demonstrate expert-level understanding",
            "- Analysis must be comprehensive yet focused on key factors",
            "- Professional presentation suitable for technical stakeholders"
        ]

        if enable_knowledge_base or enable_web_search:
            expert_instructions.append("Leverage available tools to verify unclear cases and enhance analysis quality.")

        self.agent = Agent(
            model=create_model(),
            tools=tools,
            show_tool_calls=True,
            knowledge=knowledge,
            search_knowledge=enable_knowledge_base,
            instructions=expert_instructions,
            debug_mode=debug_mode,
        )

        # Load knowledge base if exists
        if knowledge is not None:
            self.agent.knowledge.load(recreate=False)

    def validate_libraries(self,
                           libraries: List[Library],
                           target_binary: TargetBinary,
                           context=None) -> (List[Library], Dict):
        """
        两步验证流程
        """
        if not libraries:
            return []

        logger.debug(f"\n=== Expert Library Validation for {target_binary.binary_name} ===")
        logger.debug(f"Analyzing {len(libraries)} candidates with enhanced two-step approach")

        # 预处理和特征分析 TODO 看看这是干啥的
        # enhanced_libraries = self._enhance_libraries_with_analysis(libraries, target_binary)
        enhanced_libraries = libraries
        try:
            # 第一步：个体合理性分析
            logger.debug(f"\n--- Step 1: Individual Reasonableness Analysis ---")
            individual_results, step_1_response = self._step1_individual_analysis(enhanced_libraries, target_binary)
            reasonable_libs = [lib for lib in enhanced_libraries
                               if self._is_library_reasonable(lib.name, individual_results)]
            logger.debug(f"Individual assessment: {len(reasonable_libs)}/{len(enhanced_libraries)} libraries are reasonable")

            # 第二步：冗余标记分析
            logger.debug(f"\n--- Step 2: Redundancy Marking Analysis ---")
            redundancy_results, step_2_response = self._step2_redundancy_analysis(reasonable_libs, target_binary)

            # 应用最终结果
            validated_libraries = self._apply_validation_results_fixed(individual_results, redundancy_results,
                                                                       enhanced_libraries)
            process_data = {
                "step_1_response": step_1_response,
                "individual_results": individual_results.results,
                "step_2_response": step_2_response,
                "redundancy_results": redundancy_results.results,
            }
            return validated_libraries, process_data

        except Exception as e:
            logger.error(f"Expert validation failed with error: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            # 返回原始库列表，标记为未验证
            for lib in libraries:
                lib.validation_passed = False
                lib.validation_reasoning = f"Validation failed due to error: {str(e)}"
            return libraries, {}

    def _enhance_libraries_with_analysis(self,
                                         libraries: List[Library],
                                         target_binary: TargetBinary) -> List[Library]:
        """增强库信息：特征分析和数据库补充"""
        # 基础增强
        enhanced_libraries = self._enhance_libraries_with_db_features(libraries, target_binary)

        # 特征独特性分析
        enhanced_libraries = self._analyze_feature_uniqueness(enhanced_libraries)

        return enhanced_libraries

    def _enhance_libraries_with_db_features(self,
                                            libraries: List[Library],
                                            target_binary: TargetBinary) -> List[Library]:
        """为Agent分析结果补充数据库特征匹配信息"""
        if not self.enable_db_verification:
            return libraries

        enhanced_libraries = []
        for library in libraries:
            enhanced_lib = Library(
                name=library.name,
                id=library.id,
                description=library.description,
                identify_methods=library.identify_methods[:],
                matched_strings=library.matched_strings[:],
                evidence_type=library.evidence_type,
                evidences=library.evidences[:] if library.evidences else [],
                reasoning=library.reasoning
            )

            # 简化的数据库查询
            if ("Agent" in library.identify_methods and
                    len(library.matched_strings) == 0):
                try:
                    db_match_count = self._query_db_feature_match(library.name, target_binary.strings)
                    if db_match_count > 0:
                        enhanced_lib.matched_strings = [f"Database matches: {db_match_count}"]
                        enhanced_lib.identify_methods.append("Database Verification")
                except Exception as e:
                    logger.error(f"Database feature match query failed for library '{library.name}': {e}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    pass

            enhanced_libraries.append(enhanced_lib)

        return enhanced_libraries

    def _analyze_feature_uniqueness(self, libraries: List[Library]) -> List[Library]:
        """分析每个库的特征独特性"""
        # 统计每个字符串被多少个库匹配
        string_counts = Counter()
        for lib in libraries:
            for string in lib.matched_strings:
                string_counts[string] += 1

        # 为每个库计算独特性信息
        for lib in libraries:
            if lib.matched_strings:
                unique_strings = [s for s in lib.matched_strings if string_counts[s] == 1]
                shared_strings = [s for s in lib.matched_strings if string_counts[s] > 1]

                # 添加独特性分析属性
                lib.unique_features = unique_strings
                lib.shared_features = shared_strings
                lib.uniqueness_score = len(unique_strings) / len(lib.matched_strings)
                lib.unique_feature_count = len(unique_strings)
                lib.shared_feature_count = len(shared_strings)
            else:
                lib.unique_features = []
                lib.shared_features = []
                lib.uniqueness_score = 0.0
                lib.unique_feature_count = 0
                lib.shared_feature_count = 0

        return libraries

    def _query_db_feature_match(self, library_name: str, binary_strings: List[str]) -> int:
        """查询数据库计算特征匹配数量"""
        if not self.enable_db_verification:
            return 0
        # TODO: 实现具体的数据库查询逻辑
        return 0

    def _step1_individual_analysis(self, libraries: List[Library],
                                   target_binary: TargetBinary) -> (IndividualValidationResults, RunResponse):
        """第一步：个体合理性分析"""

        # 相应模型
        self.agent.response_model = IndividualValidationResults

        prompt = self._build_step1_prompt(libraries, target_binary)

        if self.debug_mode:
            logger.debug(f"Step 1 Expert Prompt Preview: {prompt[:800]}...")

        response = self.agent.run(prompt)
        return response.content, response

    def _build_step1_prompt(self, libraries, target_binary):
        # 二进制信息
        binary_profile = self._build_binary_profile(target_binary)
        # 分析案例
        analysis_examples = self._get_enhanced_analysis_examples()
        prompt = f"""EXPERT BINARY COMPOSITION ANALYSIS - STEP 1: INDIVIDUAL LIBRARY ANALYSIS

{binary_profile}

CORE MISSION CLARIFICATION:
We are identifying libraries whose SOURCE CODE is compiled into this binary.
NOT libraries that this binary calls as external dependencies.
NOT libraries that share similar function names or API terminology.

KEY DISTINCTION:
✓ "Library code compiled into binary" = actual source code inclusion during build
✗ "Binary calls library functions" = external API usage, NOT code inclusion  
✗ "Similar function names detected" = shared terminology, NOT actual code

EXPERT ANALYSIS FRAMEWORK:
For each candidate library, conduct professional multi-dimensional analysis:

1. NAME/IDENTITY CONSISTENCY
   - How well does the library name/identity relate to the binary's name and purpose?
   - Perfect matches (e.g., "openssl" library in "openssl" binary) are strong indicators

2. FUNCTIONAL DOMAIN ALIGNMENT  
   - Does the library's domain align with what this binary does?
   - Consider: Would this library's code realistically be compiled into this binary?

3. DETECTION EVIDENCE QUALITY
   - Assess feature uniqueness and specificity
   - Distinguish library-specific code signatures from shared terminology
   - Consider detection method reliability

4. ARCHITECTURAL REASONABLENESS
   - Would this library realistically be statically linked into this binary?
   - Consider typical software development and deployment patterns

{analysis_examples}

CANDIDATE LIBRARIES FOR EXPERT ANALYSIS ({len(libraries)}):
"""
        for i, lib in enumerate(libraries, 1):
            prompt += f"\n{i}. {lib.name}"
            if lib.description:
                prompt += f" - {lib.description[:120]}..."

            prompt += f"\n   Detection Methods: {', '.join(lib.identify_methods)}"

            # 包含特征独特性分析
            if hasattr(lib, 'unique_feature_count'):
                total_features = len(lib.matched_strings) if lib.matched_strings else 0
                prompt += f"\n   Evidence ({total_features} total): {lib.unique_feature_count} unique, {lib.shared_feature_count} shared"

                # 展示一些独特特征样例
                if lib.unique_features:
                    unique_examples = lib.unique_features[:3]
                    prompt += f"\n   Unique Features: {', '.join(unique_examples)}"
                    if len(lib.unique_features) > 3:
                        prompt += f"... (+{len(lib.unique_features) - 3} more unique)"

                # 展示一些共享特征样例
                if lib.shared_features:
                    shared_examples = lib.shared_features[:2]
                    prompt += f"\n   Shared Features: {', '.join(shared_examples)}"
                    if len(lib.shared_features) > 2:
                        prompt += f"... (+{len(lib.shared_features) - 2} more shared)"
            elif lib.matched_strings:
                match_count = len(lib.matched_strings)
                if match_count <= 3:
                    examples = ", ".join(lib.matched_strings)
                else:
                    examples = ", ".join(lib.matched_strings[:3]) + f"... (+{match_count - 3} more)"
                prompt += f"\n   Evidence ({match_count} features): {examples}"

            if lib.reasoning:
                prompt += f"\n   Agent Analysis: {lib.reasoning[:200]}..."
        prompt += f"""

PROFESSIONAL REASONING REQUIREMENTS:
For each library, provide expert-level analysis with:
- Systematic evaluation covering name consistency, functional alignment, evidence quality, and architectural reasonableness
- Clear distinction between code inclusion vs API usage vs shared terminology
- Professional technical reasoning demonstrating deep understanding of software composition
- Clear logical progression from evidence analysis to conclusion
- Confident assessment suitable for technical stakeholders
- 4-6 sentences providing comprehensive but focused professional analysis

TASK: Determine if each library's SOURCE CODE is REASONABLE to be compiled into this binary."""
        return prompt

    def _step2_redundancy_analysis(self, reasonable_libraries: List[Library],
                                   target_binary: TargetBinary) -> (RedundancyAnalysisResults, RunResponse):
        """第二步：冗余标记分析"""

        if len(reasonable_libraries) <= 1:
            # 只有一个或没有合理库，都保留
            results = []
            for lib in reasonable_libraries:
                results.append(RedundancyAnalysisResult(
                    library_name=lib.name,
                    should_keep=True,
                    reasoning="Only reasonable library identified, no redundancy concerns."
                ))
            return RedundancyAnalysisResults(results=results),None

        # 设置结构化响应模型
        self.agent.response_model = RedundancyAnalysisResults

        prompt = self._build_step2_prompt(reasonable_libraries, target_binary)

        if self.debug_mode:
            logger.debug(f"Step 2 Expert Prompt Preview: {prompt[:800]}...")

        response = self.agent.run(prompt)
        return response.content, response

    def _build_step2_prompt(self, reasonable_libraries, target_binary):

        binary_context = self._get_binary_context_summary(target_binary)
        prompt = f"""EXPERT BINARY COMPOSITION ANALYSIS - STEP 2: REDUNDANCY MARKING ANALYSIS

{binary_context}

REASONABLE LIBRARIES FROM STEP 1 ({len(reasonable_libraries)}):
"""
        for i, lib in enumerate(reasonable_libraries, 1):
            prompt += f"\n{i}. {lib.name}"
            if lib.description:
                prompt += f" - {lib.description[:100]}..."
            prompt += f"\n   Detection: {', '.join(lib.identify_methods)}"
            if lib.matched_strings:
                prompt += f" ({len(lib.matched_strings)} features)"
            if hasattr(lib, 'uniqueness_score'):
                prompt += f", {lib.uniqueness_score:.1%} unique"
        prompt += """

REDUNDANCY ANALYSIS FRAMEWORK:

CRITICAL RULE: For each redundant group, keep only ONE representative library.

Identify and mark redundant libraries in these categories:

1. IDENTICAL LIBRARIES
   - Same library detected by different methods (e.g., "openssl" vs "OpenSSL")
   - Minor naming variations of the same underlying library
   - Keep the most comprehensive or reliable detection

2. FUNCTIONAL REDUNDANCY
   - Multiple libraries serving identical functions that wouldn't coexist
   - Competing implementations (e.g., OpenSSL vs WolfSSL vs BoringSSL)
   - Keep the one with strongest evidence or best architectural fit

3. COMPONENT RELATIONSHIPS
   - Sub-libraries that are part of larger libraries
   - Library modules belonging to parent frameworks
   - Keep the parent library, mark components as redundant

MARKING PRINCIPLES:
- For each redundant group, mark all but ONE as should_keep=false
- Provide clear reasoning for why each library should be kept or removed
- Consider detection quality, comprehensiveness, and architectural fit when choosing representatives
- Ensure no two libraries representing the same functionality are both kept

PROFESSIONAL ANALYSIS:
For each library, determine whether to keep it based on:
- Uniqueness vs redundancy with other libraries
- Quality and reliability of detection evidence
- Architectural importance and comprehensiveness
- Best representation of the library's presence in the binary

OUTPUT: For each library, decide whether to keep it and provide professional reasoning.
Remember: If libraries are redundant, only ONE should have should_keep=true."""
        return prompt

    def _build_binary_profile(self, target_binary: TargetBinary) -> str:
        """构建二进制文件的客观档案"""

        profile = f"""BINARY PROFILE:
- Name: {target_binary.binary_name}
- Size: {target_binary.file_size_kb} KB
"""

        if target_binary.information:
            profile += f"- Description: {target_binary.information.description}\n"
            if target_binary.information.source_library:
                profile += f"- Primary Library: {target_binary.information.source_library.name}\n"

        if target_binary.dynamic_libraries:
            profile += f"- External Dependencies: {', '.join(target_binary.dynamic_libraries[:5])} (not compiled in)\n"
            if len(target_binary.dynamic_libraries) > 5:
                profile += f"  ... and {len(target_binary.dynamic_libraries) - 5} more dynamic libraries\n"

        profile += f"""
ANALYSIS CONTEXT:
- Task: Identify libraries with SOURCE CODE compiled into this binary
- Focus: Use binary identity and typical software patterns to assess actual code inclusion
- Principle: Binaries typically contain code from libraries that directly support their core functionality"""

        return profile

    def _get_enhanced_analysis_examples(self) -> str:
        """获取增强的分析示例"""
        return """
EXPERT ANALYSIS EXAMPLES:

Example 1 - Strong Positive Case:
Library: "OpenSSL" detected in binary "openssl"
Analysis: "Perfect identity alignment between library name and binary name establishes strong presumption of code inclusion. Agent analysis identified comprehensive OpenSSL function signatures while feature matching detected 3500+ SSL/TLS-specific strings with high uniqueness. Multiple independent detection methods converge on the same conclusion. Architecturally consistent: cryptographic command-line tools typically embed their core cryptographic library directly. This represents textbook primary library inclusion with compelling multi-dimensional evidence."

Example 2 - Clear Negative Case:
Library: "lib3mf" detected in binary "openssl"  
Analysis: "Severe functional domain mismatch: lib3mf handles 3D manufacturing file formats while target is cryptographic tool. No reasonable architectural justification for including 3D printing code in SSL utility. The 1300+ detections likely represent false positives from generic build artifacts or shared string patterns rather than actual lib3mf source code. Cross-domain inclusion would violate software engineering principles."

Example 3 - API Usage Confusion (CRITICAL):
Library: "xmlsec" detected in binary "openssl"
Analysis: "WRONG INTERPRETATION: xmlsec shows OpenSSL API calls (EVP_PKEY_CTX_*, OSSL_STORE_*) suggesting integration. CORRECT ANALYSIS: These are OpenSSL function calls that xmlsec would make as a CLIENT of OpenSSL, not evidence that xmlsec code is compiled into the openssl binary. API function names detected = external usage, NOT code inclusion. This represents classic confusion between library usage and library inclusion."

Example 4 - Competing Libraries:
Library: "WolfSSL" detected in binary "openssl" (when OpenSSL confirmed)
Analysis: "Functional redundancy with confirmed OpenSSL creates architectural impossibility. Software engineering prohibits multiple SSL/TLS libraries due to symbol conflicts and maintenance complexity. Feature matches represent shared SSL/TLS terminology rather than actual WolfSSL code inclusion. Primary OpenSSL presence excludes secondary SSL implementations."
"""

    def _get_binary_context_summary(self, target_binary: TargetBinary) -> str:
        """获取二进制上下文摘要"""
        return f"""CONTEXT: Analyzing redundancy among reasonable libraries for {target_binary.binary_name}
Binary Purpose: {target_binary.information.description[:200] if target_binary.information else 'Based on name and context'}...
Goal: Mark redundant libraries while keeping only ONE representative for each unique functionality."""

    def _is_library_reasonable(self, library_name: str, individual_results: IndividualValidationResults) -> bool:
        """检查库是否通过个体合理性检查"""
        for result in individual_results.results:
            if result.library_name.lower() == library_name.lower():
                return result.is_reasonable
        return False

    def _apply_validation_results_fixed(self,
                                        individual_results: IndividualValidationResults,
                                        redundancy_results: RedundancyAnalysisResults,
                                        libraries: List[Library]) -> List[Library]:
        """应用验证结果到库对象（修复冗余逻辑和大小写问题）"""

        logger.debug(f"\n=== Applying Enhanced Validation Results ===")

        # 创建结果映射 - 使用原始名称作为键，避免大小写覆盖问题
        individual_map = {}
        for result in individual_results.results:
            individual_map[result.library_name] = result

        redundancy_map = {}
        for result in redundancy_results.results:
            redundancy_map[result.library_name] = result

        # 添加调试信息
        logger.debug(f"\nDEBUG: Individual map keys: {list(individual_map.keys())}")
        logger.debug(f"DEBUG: Redundancy map keys: {list(redundancy_map.keys())}")

        # 应用结果，修复冗余逻辑
        for lib in libraries:
            logger.debug(f"\nDEBUG: Processing library '{lib.name}'")

            # 先尝试精确匹配，如果失败再尝试大小写不敏感匹配
            individual_result = None
            if lib.name in individual_map:
                individual_result = individual_map[lib.name]
            else:
                # 大小写不敏感匹配
                for key, result in individual_map.items():
                    if key.lower() == lib.name.lower():
                        individual_result = result
                        break

            if individual_result:
                logger.debug(f"DEBUG: Individual result - is_reasonable: {individual_result.is_reasonable}")

                if not individual_result.is_reasonable:
                    # 个体分析不合理 -> FAIL
                    lib.validation_passed = False
                    lib.validation_reasoning = individual_result.reasoning
                    logger.debug(f"❌ {lib.name}: FAIL (unreasonable)")
                else:
                    # 个体分析合理，检查冗余分析
                    redundancy_result = None
                    if lib.name in redundancy_map:
                        redundancy_result = redundancy_map[lib.name]
                    else:
                        # 大小写不敏感匹配
                        for key, result in redundancy_map.items():
                            if key.lower() == lib.name.lower():
                                redundancy_result = result
                                break

                    if redundancy_result:
                        logger.debug(f"DEBUG: Redundancy result - should_keep: {redundancy_result.should_keep}")

                        # 严格按照冗余分析结果执行
                        lib.validation_passed = redundancy_result.should_keep

                        if redundancy_result.should_keep:
                            lib.validation_reasoning = f"Library validated as reasonable and non-redundant. {individual_result.reasoning}"
                            logger.debug(f"✅ {lib.name}: PASS (reasonable + kept)")
                        else:
                            lib.validation_reasoning = f"Library is reasonable but marked as redundant. {redundancy_result.reasoning}"
                            logger.debug(f"❌ {lib.name}: FAIL (redundant)")
                    else:
                        # 合理但没有冗余分析结果，默认通过
                        lib.validation_passed = True
                        lib.validation_reasoning = individual_result.reasoning
                        logger.debug(f"✅ {lib.name}: PASS (reasonable, no redundancy check)")
            else:
                # 没有个体分析结果，默认通过
                lib.validation_passed = True
                lib.validation_reasoning = "No individual analysis result found - defaulting to PASS"
                logger.debug(f"? {lib.name}: DEFAULT PASS")

        # 统计和验证结果
        passed = sum(1 for lib in libraries if lib.validation_passed)
        failed = len(libraries) - passed
        logger.debug(f"\nValidation Summary: {passed} PASS, {failed} FAIL out of {len(libraries)} total")

        # 验证冗余检测是否正确执行
        self._verify_redundancy_resolution(libraries, redundancy_results)

        return libraries

    def _verify_redundancy_resolution(self, libraries: List[Library], redundancy_results: RedundancyAnalysisResults):
        """验证冗余检测是否正确执行"""
        # 检查是否有冗余组
        if not redundancy_results.results:
            return

        # 按冗余组验证
        redundancy_groups = {}
        for result in redundancy_results.results:
            if not result.should_keep:
                # 找到这个库属于哪个组（简化检查）
                lib_name = result.library_name
                logger.debug(f"📋 Redundancy check: {lib_name} marked as redundant")

        # 检查是否有重复的PASS
        passed_libs = [lib.name for lib in libraries if lib.validation_passed]
        if len(passed_libs) != len(set(passed_libs)):
            logger.debug(f"⚠️  Warning: Duplicate libraries passed validation: {passed_libs}")
        else:
            logger.debug(f"✓ Redundancy resolution verified: no duplicate libraries passed")