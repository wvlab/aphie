import argparse
import types
import typing
from collections.abc import Callable, Mapping, Sequence
from types import NoneType, UnionType
from typing import Any, TypeAliasType

from pydantic import BaseModel as PydanticBaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefinedType


def optional_action(t: type) -> type[argparse.Action]:
    class aux(argparse.Action):
        def __init__(
            self,
            option_strings: Sequence[str],
            dest: str,
            **kwargs,
        ) -> None:
            (it, n) = typing.get_args(t)
            assert isinstance(n, NoneType) or issubclass(n, NoneType)
            kwargs["nargs"] = "?"
            kwargs["type"] = it
            super().__init__(
                option_strings,
                dest,
                **kwargs,
            )

        def __call__(
            self,
            parser: argparse.ArgumentParser,
            namespace: argparse.Namespace,
            values: str | Sequence[Any] | None,
            option_string: str | None = None,
        ) -> None:
            _ = (parser, option_string)
            setattr(namespace, self.dest, values)

    return aux


class MultipleAction(argparse.Action):
    def __init__(
        self,
        option_strings: Sequence[str],
        dest: str,
        **kwargs,
    ) -> None:
        kwargs["nargs"] = "+"
        super().__init__(
            option_strings,
            dest,
            **kwargs,
        )

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


type ActionModifiers = Mapping[
    type | TypeAliasType | UnionType, Callable[[type], type[argparse.Action]]
]


def action_from_field_info(
    field: FieldInfo, modifiers: ActionModifiers | None = None
) -> type[argparse.Action]:
    mods = typing.cast(
        ActionModifiers,
        {
            bool: lambda _: argparse.BooleanOptionalAction,
            Multiple: lambda _: MultipleAction,
        }
        | dict(modifiers or {}),
    )

    assert field.annotation is not None
    if field.annotation in mods:
        return mods[field.annotation](field.annotation)

    origin = typing.get_origin(field.annotation)
    targs = typing.get_args(field.annotation)
    match (origin, targs):
        case (t, _) if t in mods and t is not None:
            return mods[t](field.annotation or t)

        case (types.UnionType | typing.Union, (_, types.NoneType)):
            return optional_action(field.annotation)

    return argparse._StoreAction


def add_model_to_parser(
    parser: argparse.ArgumentParser,
    model: type[PydanticBaseModel],
    actions: ActionModifiers | None = None,
) -> None:
    for name, field in model.model_fields.items():
        alias = (f"-{field.alias}",) if field.alias is not None else tuple()

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
