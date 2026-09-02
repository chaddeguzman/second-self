# Charlie — Patterns Library

> My personal reference of patterns that worked and anti-patterns to avoid.
> Grows via the lessons-learned loop: after each build, I add what worked
> or what failed. Scanned during my boot sequence and before every new build.

## Patterns that worked

- **argparse subcommand pattern with global config flag** — `add_argument("--base-dir")` on the main parser before subparsers; each subcommand is a `_command_*` function dispatched via `set_defaults(func=...)`. Clean separation: config on main, command-specific args on sub. When to use: any CLI tool with subcommands that share a config option. Source: echo-session CLI build.

## Anti-patterns to avoid

<!-- One entry per anti-pattern: what, why it failed, source task -->

(empty — will fill as I complete builds)