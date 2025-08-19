import unittest
import argparse
from aphie import parse, BaseModel, Field, Multiple
from pathlib import Path


class TestParseArgs(unittest.TestCase):
    def test_simple_global_args(self):
        class GlobalArgs(BaseModel):
            verbose: bool = False
            level: int = 0

        args, subcommand_args = parse(GlobalArgs, args=["--verbose", "--level", "5"])
        self.assertTrue(args.verbose)
        self.assertEqual(args.level, 5)
        self.assertIsNone(subcommand_args)

    def test_global_args_with_defaults(self):
        class GlobalArgs(BaseModel):
            verbose: bool = False
            level: int = 0

        global_args, subcommand_args = parse(GlobalArgs, args=[])
        self.assertFalse(global_args.verbose)
        self.assertEqual(global_args.level, 0)
        self.assertIsNone(subcommand_args)

    def test_with_subcommand(self):
        class GlobalArgs(BaseModel):
            verbose: bool = False

        class SubCommandArgs(BaseModel):
            name: str
            count: int = 1

        subcommands = {"run": SubCommandArgs}
        global_args, subcommand_args = parse(
            GlobalArgs, subcommands, args=["run", "--name", "test", "--count", "3"]
        )
        self.assertFalse(global_args.verbose)
        self.assertEqual(subcommand_args.name, "test")
        self.assertEqual(subcommand_args.count, 3)

    def test_with_subcommand_and_global_args(self):
        class GlobalArgs(BaseModel):
            verbose: bool = False

        class SubCommandArgs(BaseModel):
            name: str

        subcommands = {"run": SubCommandArgs}
        global_args, subcommand_args = parse(
            GlobalArgs, subcommands, args=["--verbose", "run", "--name", "test"]
        )
        self.assertTrue(global_args.verbose)
        self.assertEqual(subcommand_args.name, "test")

    def test_required_argument_missing(self):
        class GlobalArgs(BaseModel):
            required_arg: str

        with self.assertRaises(SystemExit):
            parse(GlobalArgs, args=[])

    def test_custom_action(self):
        class StoreTrueAction(argparse.Action):
            def __call__(self, parser, namespace, values, option_string=None):
                setattr(namespace, self.dest, True)

        class GlobalArgs(BaseModel):
            custom: bool = False

        actions = {bool: StoreTrueAction}

        global_args, _ = parse(GlobalArgs, actions=actions, args=["--custom"])
        self.assertTrue(global_args.custom)

    def test_field_alias(self):
        class GlobalArgs(BaseModel):
            level: int = Field(0, alias="l")

        global_args, _ = parse(GlobalArgs, args=["-l", "10"])
        self.assertEqual(global_args.level, 10)

    def test_multiple_strings(self):
        class GlobalArgs(BaseModel):
            files: Multiple[str]

        args, _ = parse(GlobalArgs, args=["--files", "a.txt", "b.txt", "c.txt"])
        self.assertEqual(args.files, ["a.txt", "b.txt", "c.txt"])

    def test_multiple_ints(self):
        class GlobalArgs(BaseModel):
            numbers: Multiple[int]

        args, _ = parse(GlobalArgs, args=["--numbers", "1", "2", "3"])
        self.assertEqual(args.numbers, [1, 2, 3])
        self.assertTrue(all(isinstance(x, int) for x in args.numbers))

    def test_multiple_defaults_empty(self):
        class GlobalArgs(BaseModel):
            files: Multiple[str] = []

        args, _ = parse(GlobalArgs, args=[])
        self.assertEqual(args.files, [])

    def test_multiple_occurrences_extend(self):
        class GlobalArgs(BaseModel):
            tags: Multiple[str]

        args, _ = parse(GlobalArgs, args=["--tags", "a", "b", "--tags", "c"])
        self.assertEqual(args.tags, ["a", "b", "c"])

    def test_optional_alias(self):
        class GlobalArgs(BaseModel):
            string: str | None = Field(None, alias="s")

        global_args, _ = parse(GlobalArgs, args=["--string", "string"])
        self.assertEqual(global_args.string, "string")

    def test_optional_path(self):
        class GlobalArgs(BaseModel):
            path: Path | None = Field(None, alias="p")

        args, _ = parse(GlobalArgs, args=["-p", "/tmp/test"])
        self.assertEqual(args.path, Path("/tmp/test"))

        args, _ = parse(GlobalArgs, args=[])
        self.assertIsNone(args.path)
