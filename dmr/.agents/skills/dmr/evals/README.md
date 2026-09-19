# Evals for the `dmr` skill

Behavioral tests for this skill, run with
[`claude plugin eval`](https://code.claude.com/docs/en/plugin-evals).
Every case is a prompt a user could type plus graders that check
the answer and whether the skill was the reason for it.

```bash
cd dmr/.agents/skills/dmr
claude plugin eval . --no-publish
claude plugin eval . --case create-endpoint --runs 1 --ablation none
```

Each case runs with and without the skill, `Δ` in the summary is what
the skill contributes. `results/` is written by every run and is ignored by git.
CI runs the suite on a schedule from `.github/workflows/skill-evals.yml`.
