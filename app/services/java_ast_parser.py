from dataclasses import dataclass

import tree_sitter_java
from tree_sitter import Language, Node, Parser

JAVA_LANGUAGE = Language(
    tree_sitter_java.language()
)

JAVA_PARSER = Parser(JAVA_LANGUAGE)


@dataclass(frozen=True, slots=True)
class JavaSymbol:
    """Java AST에서 추출한 코드 심볼."""

    symbol_type: str
    symbol_name: str

    package_name: str | None
    class_name: str | None

    start_line: int
    end_line: int

    content: str


def node_text(
    node: Node,
    source: bytes,
) -> str:
    return source[
        node.start_byte : node.end_byte
    ].decode(
        "utf-8",
        errors="replace",
    )


def child_text_by_field(
    node: Node,
    field_name: str,
    source: bytes,
) -> str | None:
    child = node.child_by_field_name(
        field_name
    )

    if child is None:
        return None

    return node_text(
        child,
        source,
    )


def find_package_name(
    root: Node,
    source: bytes,
) -> str | None:
    """package declaration을 찾는다."""

    for child in root.children:
        if child.type != "package_declaration":
            continue

        text = node_text(
            child,
            source,
        )

        text = (
            text
            .removeprefix("package")
            .removesuffix(";")
            .strip()
        )

        return text

    return None

def extract_java_symbols(
    content: str,
) -> list[JavaSymbol]:
    """Java 코드에서 class와 method를 추출한다."""

    source = content.encode("utf-8")

    tree = JAVA_PARSER.parse(source)

    root = tree.root_node

    package_name = find_package_name(
        root,
        source,
    )

    symbols: list[JavaSymbol] = []

    def walk(
        node: Node,
        current_class: str | None = None,
    ) -> None:
        class_name = current_class

        if node.type in {
            "class_declaration",
            "interface_declaration",
            "enum_declaration",
            "record_declaration",
        }:
            name = child_text_by_field(
                node,
                "name",
                source,
            )

            if name:
                class_name = name

                symbols.append(
                    JavaSymbol(
                        symbol_type="class",
                        symbol_name=name,
                        package_name=package_name,
                        class_name=name,
                        start_line=(
                            node.start_point.row + 1
                        ),
                        end_line=(
                            node.end_point.row + 1
                        ),
                        content=node_text(
                            node,
                            source,
                        ),
                    )
                )

        elif node.type == "method_declaration":
            method_name = child_text_by_field(
                node,
                "name",
                source,
            )

            if method_name:
                symbols.append(
                    JavaSymbol(
                        symbol_type="method",
                        symbol_name=method_name,
                        package_name=package_name,
                        class_name=class_name,
                        start_line=(
                            node.start_point.row + 1
                        ),
                        end_line=(
                            node.end_point.row + 1
                        ),
                        content=node_text(
                            node,
                            source,
                        ),
                    )
                )

        elif node.type == "constructor_declaration":
            constructor_name = (
                child_text_by_field(
                    node,
                    "name",
                    source,
                )
            )

            if constructor_name:
                symbols.append(
                    JavaSymbol(
                        symbol_type="constructor",
                        symbol_name=constructor_name,
                        package_name=package_name,
                        class_name=class_name,
                        start_line=(
                            node.start_point.row + 1
                        ),
                        end_line=(
                            node.end_point.row + 1
                        ),
                        content=node_text(
                            node,
                            source,
                        ),
                    )
                )

        for child in node.children:
            walk(
                child,
                current_class=class_name,
            )

    walk(root)

    return symbols

@dataclass(frozen=True, slots=True)
class JavaMethodCall:
    caller_class: str | None
    caller_method: str

    receiver: str | None

    callee_name: str
    inferred_callee_class: str | None

    line_number: int
    
def normalize_receiver_name(
    receiver: str | None,
) -> str | None:
    if receiver is None:
        return None

    receiver = receiver.strip()

    if not receiver:
        return None

    # this.userService -> userService
    if receiver.startswith("this."):
        return receiver.rsplit(".", 1)[-1]

    return receiver

def extract_field_types(
    content: str,
) -> dict[str, dict[str, str]]:
    """
    class별 field 변수의 타입을 추출한다.

    예:
    {
        "UserController": {
            "userService": "UserService"
        }
    }
    """

    source = content.encode("utf-8")
    tree = JAVA_PARSER.parse(source)

    result: dict[str, dict[str, str]] = {}

    def walk(
        node: Node,
        current_class: str | None = None,
    ) -> None:
        class_name = current_class

        if node.type in {
            "class_declaration",
            "interface_declaration",
            "record_declaration",
        }:
            name = child_text_by_field(
                node,
                "name",
                source,
            )

            if name:
                class_name = name
                result.setdefault(
                    class_name,
                    {},
                )

        if (
            node.type == "field_declaration"
            and class_name is not None
        ):
            type_node = node.child_by_field_name(
                "type"
            )

            if type_node is not None:
                field_type = node_text(
                    type_node,
                    source,
                )

                for child in node.children:
                    if child.type != "variable_declarator":
                        continue

                    name_node = (
                        child.child_by_field_name(
                            "name"
                        )
                    )

                    if name_node is None:
                        continue

                    variable_name = node_text(
                        name_node,
                        source,
                    )

                    result[class_name][
                        variable_name
                    ] = field_type

        for child in node.children:
            walk(
                child,
                current_class=class_name,
            )

    walk(tree.root_node)

    return result

def extract_java_method_calls(
    content: str,
) -> list[JavaMethodCall]:
    """Java 메서드 내부의 method invocation을 추출한다."""

    source = content.encode("utf-8")
    tree = JAVA_PARSER.parse(source)

    field_types = extract_field_types(
        content
    )

    calls: list[JavaMethodCall] = []

    def walk(
        node: Node,
        current_class: str | None = None,
        current_method: str | None = None,
    ) -> None:
        class_name = current_class
        method_name = current_method

        if node.type in {
            "class_declaration",
            "interface_declaration",
            "record_declaration",
        }:
            name = child_text_by_field(
                node,
                "name",
                source,
            )

            if name:
                class_name = name

        if node.type in {
            "method_declaration",
            "constructor_declaration",
        }:
            name = child_text_by_field(
                node,
                "name",
                source,
            )

            if name:
                method_name = name

        if (
            node.type == "method_invocation"
            and method_name is not None
        ):
            name_node = node.child_by_field_name(
                "name"
            )

            object_node = node.child_by_field_name(
                "object"
            )

            if name_node is not None:
                callee_name = node_text(
                    name_node,
                    source,
                )

                receiver = (
                    node_text(
                        object_node,
                        source,
                    )
                    if object_node is not None
                    else None
                )

                normalized_receiver = (
                    normalize_receiver_name(
                        receiver
                    )
                )

                inferred_class: str | None = None

                # foo() → 같은 class의 method로 우선 추론
                if normalized_receiver is None or normalized_receiver == "this":
                    inferred_class = class_name

                # userService.foo()
                elif class_name is not None:
                    inferred_class = (
                        field_types
                        .get(
                            class_name,
                            {},
                        )
                        .get(
                            normalized_receiver
                        )
                    )

                # UserService.staticMethod()
                if (
                    inferred_class is None
                    and normalized_receiver
                    and normalized_receiver[0].isupper()
                    and "." not in normalized_receiver
                ):
                    inferred_class = (
                        normalized_receiver
                    )

                calls.append(
                    JavaMethodCall(
                        caller_class=class_name,
                        caller_method=method_name,
                        receiver=receiver,
                        callee_name=callee_name,
                        inferred_callee_class=(
                            inferred_class
                        ),
                        line_number=(
                            node.start_point.row + 1
                        ),
                    )
                )

        for child in node.children:
            walk(
                child,
                current_class=class_name,
                current_method=method_name,
            )

    walk(tree.root_node)

    return calls