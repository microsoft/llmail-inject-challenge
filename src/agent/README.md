# Agent

The agent receives `JobMessage`s from a queue.
`GeneralWorkload` takes care of routing the message to the specific scenario (`ScenarioWorkload`).
Challenge scenarios are described in `config.yaml`; each scenario is defined by an LLM (e.g., GPT4
or Phi3), and one or more defenses.

## Local development

To try this out locally:

```bash
pip install -r requirements.txt
sudo mkdir -p /disk1/models
sudo chown -R <your-user> /disk`
```

Then

```bash
python __main__.py local
```

At this point, the message defined in `job.json` will be sent to the agent, which will execute it.