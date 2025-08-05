import argparse
import builtins
import typing
from collections.abc import Mapping, Sequence

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefinedType

type ActionModifiers = Mapping[type, type[argparse.Action]]


def action_from_field_info(
    field: FieldInfo, modifiers: ActionModifiers | None = None
) -> type[argparse.Action]:
    match field.annotation:
        case None:
            raise ValueError("Field annotation cannot be None")

        case t if modifiers is not None and t in modifiers:
            return modifiers[t]

        case builtins.bool:
            return argparse.BooleanOptionalAction

        case _:
            return argparse._StoreAction


def add_model_to_parser(
    parser: argparse.ArgumentParser,
    model: type[BaseModel],
    actions: ActionModifiers | None = None,
) -> None:
    for name, field in model.model_fields.items():
        alias = field.alias and (f"-{field.alias}",) or tuple()

        action = action_from_field_info(field, actions)
        kwargs = {
            "dest": name,
            "action": action,
            "default": field.default,
            "required": isinstance(field.default, PydanticUndefinedType),
        }

        if action is argparse._StoreAction:
            kwargs["type"] = field.annotation or str

        parser.add_argument(f"--{name.replace('_', '-')}", *alias, **kwargs)


def parser(
    g: type[BaseModel],
    subcommands: Mapping[str, type[BaseModel]] | None = None,
    actions: ActionModifiers | None = None,
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    add_model_to_parser(parser, g)

    if subcommands is not None:
        subparsers = parser.add_subparsers(dest="command", required=True)
        for c, m in subcommands.items():
            p = subparsers.add_parser(c)
            add_model_to_parser(p, m, actions)

    return parser


@typing.overload
def parse_args[GT: BaseModel](
    g: type[GT],
    subcommands: None = None,
    *,
    args: Sequence[str] | None = None,
    actions: ActionModifiers | None = None,
) -> tuple[GT, None]: ...


@typing.overload
def parse_args[GT: BaseModel, ST: BaseModel](
    g: type[GT],
    subcommands: Mapping[str, type[ST]],
    *,
    args: Sequence[str] | None = None,
    actions: ActionModifiers | None = None,
) -> tuple[GT, ST]: ...


def parse_args[GT: BaseModel, ST: BaseModel](
    g: type[GT],
    subcommands: Mapping[str, type[ST]] | None = None,
    *,
    args: Sequence[str] | None = None,
    actions: ActionModifiers | None = None,
) -> tuple[GT, ST | None]:
    parsed = vars(parser(g, subcommands, actions).parse_args(args))

    subcommand_args = None
    if subcommands is not None:
        command = parsed.pop("command")
        subcommand_args = subcommands[command].model_validate(parsed)

    global_args = g.model_validate(parsed)
    return global_args, subcommand_args
