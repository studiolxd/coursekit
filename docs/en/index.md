# coursekit documentation

coursekit turns a folder into an AI-assisted e-learning course production project, with people signing off at every control point.

## What coursekit is

coursekit is a command-line tool (`coursekit`) that drives the production of e-learning courses through a fixed process:

1. **Brief**: you drop the reference material (documents, links, notes) and coursekit converts it for the agents.
2. **Instructional design**: an agent proposes units, sections, objectives and hours; **you sign it off**.
3. **Writing**: an agent writes each unit in a fixed Markdown format, and `coursekit verify` checks it against the production rules.
4. **AI review**: a second agent (another tool or model) reviews each unit.
5. **Editorial review and sign-off**: **you read each unit and sign it off**.
6. **Media**: images, graphics, video, audio and demos are planned and produced.
7. **Assembly**: the approved Markdown is loaded into the authoring platform (SLXD Creator), never the other way round.
8. **Client review** and **delivery**: SCORM packages are exported, recorded and published to a shared folder with a tracking spreadsheet.

The agents do the drafting; the decisions stay with people. Only a person can sign (`coursekit approve`): the generated agent settings forbid agents to run it.

coursekit works with [Claude Code](https://claude.com/claude-code), opencode and Codex, interchangeably, and runs on macOS, Windows and Linux.

## Who it is for

- **Production leads and instructional designers** who sign off designs and units and follow each course with `coursekit status`.
- **Editors and reviewers** who read units and sign them.
- **Technical owners** who set up the project, the machines, the agent tools and the shared folder.

You do not need to program. You need a terminal and one of the supported AI tools.

## Documentation map

| File | What it covers |
|---|---|
| [Getting started](01-getting-started.md) | requirements, installation, `coursekit init` step by step, the first course |
| [Workflow](02-workflow.md) | the whole process, course and unit statuses, who does what, changes after approval |
| [Commands](03-commands.md) | every command and option |
| [Configuration](04-configuration.md) | `project.yaml`, `.env`, `config/`, `course.yaml` |
| [Agents](05-agents.md) | Claude Code, opencode, Codex, roles, models, skills, MCP |
| [Content](06-content.md) | course folders, content format, directives, verification |
| [Media](07-media.md) | planning and producing media, voice, subtitles |
| [Assembly and delivery](08-assembly-and-delivery.md) | SLXD Creator, SCORM, shared folder, catalog |
| [Troubleshooting](09-troubleshooting.md) | `coursekit doctor`, `coursekit setup`, common problems, FAQ |

## Quick start

```bash
uv tool install git+https://github.com/studiolxd/coursekit
coursekit init acme-courses
cd acme-courses
coursekit doctor
coursekit run new-course "Strong passwords" 2 --code PWD
```

The same last step works inside your AI tool: open it in the project folder and type `/new-course "Strong passwords" 2 --code PWD`. Then `coursekit status` always tells you where each course is and what the next step is.

Next: [Getting started](01-getting-started.md)
