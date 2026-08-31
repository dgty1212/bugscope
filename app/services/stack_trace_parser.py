import re

from app.schemas.stack_trace import (
    ParsedStackTrace,
    StackFrame,
)

STACK_FRAME_PATTERN = re.compile(
    r"""
    ^\s*at\s+
    (?P<qualified_class>[\w.$]+)
    \.
    (?P<method>[\w$<>]+)
    \(
        (?:
            Native\s+Method
            |
            Unknown\s+Source
            |
            (?P<file>[^():]+)
            (?:
                :
                (?P<line>\d+)
            )?
        )
    \)
    """,
    re.VERBOSE,
)


EXCEPTION_PATTERN = re.compile(
    r"""
    ^
    (?P<exception>
        [A-Za-z_$][\w.$]*
        (?:Exception|Error)
    )
    (?:
        :\s*
        (?P<message>.*)
    )?
    $
    """,
    re.VERBOSE,
)


def parse_stack_trace(
    error_log: str,
) -> ParsedStackTrace:
    """Java stack trace 문자열을 구조화한다."""

    lines = [
        line.rstrip()
        for line in error_log.splitlines()
        if line.strip()
    ]

    exception_type: str | None = None
    message: str | None = None

    frames: list[StackFrame] = []

    for line in lines:
        if exception_type is None:
            exception_match = EXCEPTION_PATTERN.match(
                line.strip()
            )

            if exception_match:
                exception_type = (
                    exception_match.group("exception")
                )

                message = (
                    exception_match.group("message")
                    or None
                )

        frame_match = STACK_FRAME_PATTERN.match(line)

        if not frame_match:
            continue

        qualified_class = frame_match.group(
            "qualified_class"
        )

        # Inner class는 Outer$Inner 형태일 수 있음
        short_class_name = qualified_class.rsplit(
            ".",
            1,
        )[-1]

        if "." in qualified_class:
            package_name = qualified_class.rsplit(
                ".",
                1,
            )[0]
        else:
            package_name = None

        line_text = frame_match.group("line")

        frames.append(
            StackFrame(
                raw=line.strip(),
                package_name=package_name,
                class_name=short_class_name,
                method_name=frame_match.group("method"),
                file_name=frame_match.group("file"),
                line_number=(
                    int(line_text)
                    if line_text is not None
                    else None
                ),
                depth=len(frames),
            )
        )

    return ParsedStackTrace(
        exception_type=exception_type,
        message=message,
        frames=frames,
    )