# streaming-langgraph

an example of streaming output from langgraph to a fastAPI endpoint

### installation instruction

- recommended: use a Python virtual environement

```bash
pip install -r requirements.txt
```

## running instruction

- required: create a `.env` file and ensure that it contains a valid `OPENAI_API_KEY`

```bash
python -m main
```

## testing instruction

```bash
curl http://localhost:8000/chat
```
