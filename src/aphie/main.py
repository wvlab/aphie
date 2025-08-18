import argparse
import builtins
import typing
from typing import Any, TypeAliasType
from collections.abc import Mapping, Sequence

from pydantic import BaseModel as PydanticBaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefinedType


class MultipleAction(argparse.Action):
    def __init__(self, option_strings, dest, **kwargs):
        kwargs.setdefault("nargs", "+")
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        _ = (parser, option_string)
        current = getattr(namespace, self.dest, None)
        if current is None or isinstance(current, PydanticUndefinedType):
            current = []

        assert isinstance(values, Sequence)
        current.extend(values)
        setattr(namespace, self.dest, current)


type Multiple[T] = Sequence[T]


class BaseModel(PydanticBaseModel, validate_by_name=True):
    pass


type ActionModifiers = Mapping[type, type[argparse.Action]]


def action_from_field_info(
    field: FieldInfo, modifiers: ActionModifiers | None = None
) -> type[argparse.Action]:
    annotation = (
        typing.get_origin(field.annotation) or field.annotation,
        typing.get_args(field.annotation),
    )

    match annotation:
        case (None, _):
            raise ValueError("Field annotation cannot be None")

        case (t, _) if modifiers is not None and t in modifiers:
            return modifiers[t]

        case (builtins.bool, ()):
            return argparse.BooleanOptionalAction

        case (t, (_)) if t == Multiple:
            return MultipleAction

        case _:
            return argparse._StoreAction


def add_model_to_parser(
    parser: argparse.ArgumentParser,
    model: type[PydanticBaseModel],
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
    g: type[PydanticBaseModel],
    subcommands: Mapping[str, type[PydanticBaseModel]] | None = None,
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
def parse_args[GT: PydanticBaseModel](
    g: type[GT],
    subcommands: None = None,
    *,
    args: Sequence[str] | None = None,
    actions: ActionModifiers | None = None,
) -> tuple[GT, None]: ...


@typing.overload
def parse_args[GT: PydanticBaseModel, ST: PydanticBaseModel](
    g: type[GT],
    subcommands: Mapping[str, type[ST]],
    *,
    args: Sequence[str] | None = None,
    actions: ActionModifiers | None = None,
) -> tuple[GT, ST]: ...


def parse_args[GT: PydanticBaseModel, ST: PydanticBaseModel](
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
