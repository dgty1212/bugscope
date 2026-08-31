from pydantic import BaseModel


class StackFrame(BaseModel):
    """Java stack trace의 한 프레임."""

    raw: str

    package_name: str | None
    class_name: str
    method_name: str

    file_name: str | None
    line_number: int | None

    depth: int


class ParsedStackTrace(BaseModel):
    """파싱된 Java stack trace."""

    exception_type: str | None
    message: str | None

    frames: list[StackFrame]
    
class StackTraceAnalyzeRequest(BaseModel):
    error_log: str