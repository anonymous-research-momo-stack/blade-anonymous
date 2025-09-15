from typing import Optional, List

from pydantic import BaseModel, Field


# bin info finder
class LibraryInformation(BaseModel):
    """
    Agent answer format for library information
    """
    name: str = Field(
        description="The name of the third-party library."
    )
    description: str = Field(
        description="A concise description of the third-party library."
    )

    def customer_serialize(self) -> dict:
        """
        Custom serialization to ensure all fields are included
        """
        return {
            "name": self.name,
            "description": self.description
        }

    @classmethod
    def init_from_dict(cls, data: dict):
        """
        Initialize from a dictionary, ensuring all fields are set
        """
        return cls(
            name=data.get("name", ""),
            description=data.get("description", "")
        )

# bin info finder
class BinaryInformation(BaseModel):
    """
    Agent answer format for binary analysis
    """
    name: str = Field(
        description="The name of this binary."
    )
    description: str = Field(
        description="Comprehensive description of the binary, including what it is, its main function, common use cases, security considerations, and any other useful information about this binary."
    )
    source_library: Optional[LibraryInformation] = Field(
        default=None,
        description="Information about the library or framework that may have compiled or generated this binary (if applicable)."
    )

    def customer_serialize(self) -> dict:
        """
        Custom serialization to ensure all fields are included
        """
        return {
            "name": self.name,
            "description": self.description,
            "source_library": self.source_library.customer_serialize() if self.source_library else None
        }

    @classmethod
    def init_from_dict(cls, data: dict):
        """
        Initialize from a dictionary, ensuring all fields are set
        """
        source_library_data = data.get("source_library", None)
        source_library = LibraryInformation.init_from_dict(source_library_data) if source_library_data else None

        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            source_library=source_library
        )

# tpl analyzer
class LibraryResult(BaseModel):
    """
    Agent response model for library analysis
    """
    name: str = Field(description="Canonical library name - use GitHub repository name or common package manager name (e.g., 'protobuf', 'opencv', 'libidn'), Do not include space.")
    full_name: str = Field(description="Complete official library name (e.g., 'Protocol Buffers', 'GNU Libidn', 'Apache Thrift'), if available")
    description: str = Field(
        description="Brief description, include full name if different from name, mention repository if known")
    evidence_type: str = Field(description="Evidence type: Explicit, Implicit, or Mixed")
    evidences: List[str] = Field(description="Actual evidence strings from the binary that support this identification")
    reasoning: str = Field(
        description="Explanation of what specific evidence indicates this library's code is present in the binary")

    def customer_serialize(self) -> dict:
        """
        Custom serialization to ensure all fields are included
        """
        return {
            "name": self.name,
            "description": self.description,
            "evidence_type": self.evidence_type,
            "evidences": self.evidences,
            "reasoning": self.reasoning
        }

    @classmethod
    def init_from_dict(cls, data: dict):
        """
        Initialize from a dictionary, ensuring all fields are set
        """
        return cls(
            name=data.get("name", ""),
            full_name=data.get("full_name", ""),
            description=data.get("description", ""),
            evidence_type=data.get("evidence_type", ""),
            evidences=data.get("evidences", []),
            reasoning=data.get("reasoning", "")
        )

# tpl analyzer
class TPLAnalysisResult(BaseModel):
    """
    Agent response model for complete TPL analysis
    """
    analysis_summary:str = Field(description="Concise summary of the overall third-party library analysis results")
    libraries: List[LibraryResult] = Field(description="List of identified third-party libraries")

# validator
class LibraryValidationResult(BaseModel):
    """Individual library validation result"""
    library_name: str = Field(description="Library name exactly as provided")
    is_reasonable: bool = Field(description="Whether this library could reasonably be compiled into the binary")
    reasoning: str = Field(description="Professional multi-dimensional analysis explaining the decision")
    confidence: str = Field(description="HIGH/MEDIUM/LOW confidence level")

    def customer_serialize(self) -> dict:
        """
        Custom serialization to ensure all fields are included
        """
        return {
            "library_name": self.library_name,
            "is_reasonable": self.is_reasonable,
            "reasoning": self.reasoning,
            "confidence": self.confidence
        }

    @classmethod
    def init_from_dict(cls, data:dict):
        """
        Initialize from a dictionary, ensuring all fields are set
        """
        return cls(
            library_name=data.get("library_name", ""),
            is_reasonable=data.get("is_reasonable", False),
            reasoning=data.get("reasoning", ""),
            confidence=data.get("confidence", "LOW")
        )

# validator
class IndividualValidationResults(BaseModel):
    """Step 1 individual validation results"""
    results: List[LibraryValidationResult] = Field(description="Individual validation results for all libraries")

# validator
class RedundancyAnalysisResult(BaseModel):
    """Redundancy analysis result"""
    library_name: str = Field(description="Library name exactly as provided")
    should_keep: bool = Field(description="Whether this library should be kept")
    reasoning: str = Field(description="Professional analysis explaining why keep or remove")

    def customer_serialize(self) -> dict:
        """
        Custom serialization to ensure all fields are included
        """
        return {
            "library_name": self.library_name,
            "should_keep": self.should_keep,
            "reasoning": self.reasoning
        }

    @classmethod
    def init_from_dict(cls, data:dict):
        """
        Initialize from a dictionary, ensuring all fields are set
        """
        return cls(
            library_name=data.get("library_name", ""),
            should_keep=data.get("should_keep", False),
            reasoning=data.get("reasoning", "")
        )

# validator
class RedundancyAnalysisResults(BaseModel):
    """Step 2 redundancy analysis results"""
    results: List[RedundancyAnalysisResult] = Field(
        description="Redundancy analysis results for all reasonable libraries")


class SoftwareContext(BaseModel):
    """Software context analysis results"""
    software_type: str = Field(default="unknown",
                               description="Software type: embedded_system, web_application, mobile_app, desktop_application, library, system_utility, database")
    primary_purpose: str = Field(default="", description="Primary function and purpose description")
    technology_stack: List[str] = Field(default_factory=list, description="Detected technology stack and frameworks")
    deployment_environment: str = Field(default="unknown",
                                        description="Inferred deployment environment: embedded, server, desktop, mobile, etc.")
    key_components: List[str] = Field(default_factory=list, description="Identified key components and modules")
    directory_analysis: str = Field(default="", description="Directory structure analysis summary")
    architecture_pattern: str = Field(default="unknown", description="Identified software architecture pattern")
    build_system: str = Field(default="unknown", description="Build system type: make, cmake, autotools, etc.")
    confidence_level: str = Field(default="LOW", description="Analysis confidence level: HIGH/MEDIUM/LOW")

    def customer_serialize(self) -> dict:
        """
        Custom serialization to ensure all fields are included
        """
        return {
            "software_type": self.software_type,
            "primary_purpose": self.primary_purpose,
            "technology_stack": self.technology_stack,
            "deployment_environment": self.deployment_environment,
            "key_components": self.key_components,
            "directory_analysis": self.directory_analysis,
            "architecture_pattern": self.architecture_pattern,
            "build_system": self.build_system,
            "confidence_level": self.confidence_level
        }
