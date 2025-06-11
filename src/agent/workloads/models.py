from pydantic import BaseModel


class ToolCall(BaseModel):
    """Tool call information."""

    name: str
    arguments: dict


class LLMResponse(BaseModel):
    """Response from the LLM model."""

    response: str
    tool_calls: list[ToolCall]
