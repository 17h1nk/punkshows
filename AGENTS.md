# Working notes for the agent

You work only inside this folder. You run on a local model with a limited context; the conversation is
compacted (summarized) automatically when it fills up, and you may lose details that are not written down.

## Memory: keep PROGRESS.md up to date
- At the start of every session or after a compaction, read `PROGRESS.md` (create it if missing).
- For each task, record in `PROGRESS.md`: the goal, the plan as a checklist, what is done, what is next,
  decisions made and why, and any problems or dead ends. Update it after every meaningful step, not only at the end.
- Keep it short and current: rewrite stale parts rather than appending endlessly.
- Use the todo list for the current step-by-step plan, and PROGRESS.md for anything that must survive.

## Working style
- Break big tasks into small steps; check each step works before moving on.
- If the same approach fails twice, stop, write down what failed in PROGRESS.md, and try something different
  or ask the user.
- Ask before deleting files.
