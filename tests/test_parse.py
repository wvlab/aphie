import unittest
import argparse
from aphie import parse, BaseModel, Field


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
