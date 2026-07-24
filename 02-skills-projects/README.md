# Skills and Projects

`02-skills-projects` is the execution layer of Second Self. Layer 1 supplies
personal context, priorities, knowledge, and intent. Codex or Claude then acts
as a digital employee: it uses the appropriate skills and commands to perform
project work, produce an output, evaluate feedback, and continue until the goal
is met.

## Operating Loop

```text
Input from Layer 1
        |
        v
Codex or Claude selects and uses skills or commands
        |
        v
Project work produces an output
        |
        v
Feedback evaluates the result
        |
        +---- Goal not met: return to project work with the new feedback
        |
        +---- Goal met: retain the result and write back relevant learning
```

The loop is iterative. Feedback may come from the user, tests, review results,
project stakeholders, or the output itself. Each pass should improve the work
without losing the original intent supplied by Layer 1.

## Folder Guide

### `skills`

Contains reusable skills, commands, procedures, and operating instructions that
teach Codex or Claude how to perform specialized work.

Skills are the capabilities used by the digital employee. They should describe
repeatable methods rather than store private project data.

`second-self-wiki` processes Raw sources, refreshes changed curated notes,
queries linked knowledge with primary evidence, and performs structural or
semantic wiki maintenance through protected broker proposals.

### `projects`

Stores each user's local projects and their working context. A project may
contain its objectives, status, decisions, next actions, outputs, supporting
files, or a local project repository.

The folder is committed only as an empty placeholder. Everything placed inside
it remains local and is ignored by Git, except for the scaffold `.gitkeep`
file. This allows every cloned Second Self repository to include a ready-to-use
projects folder without publishing private project information.

#### Using independent Git repositories

Complete Terminal and VS Code instructions for cloning and managing independent
project repositories are maintained in
[Working with Project Repositories](<../Quick Start.md#working-with-project-repositories>)
in the Quick Start guide.

## How Layer 1 and Layer 2 Work Together

1. Layer 1 provides the relevant identity, strategy, notes, references,
   commitments, or review context.
2. Codex or Claude chooses the skills and commands required for the task.
3. The selected project stores the active working context and generated
   outputs.
4. Feedback is evaluated and applied through another project-work cycle.
5. When the goal is met, the project retains its result.
6. Consequential decisions, status changes, and reusable personal lessons may
   return to Second Self through the project writeback process.

Layer 1 remains the source of personal direction. Layer 2 turns that direction
into project execution while keeping the work auditable and private.

## Privacy

- Do not commit files or subfolders inside `projects`.
- Commit and push nested project repositories only through their own Git
  remotes.
- Do not place credentials, secrets, or private exports in tracked skill files.
- Keep project-specific execution material in its project folder.
- Return broader personal lessons or decisions through the controlled
  writeback and review workflows.
