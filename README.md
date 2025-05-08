# ~~image2vec-server~~

## Running in container (using docker, offhand)

In the root directory of this project, execute this command.
- When you run the container, replace ip and port of host to your wanted.

```bash
docker build -t ai-server .
docker run -it -p 000.000.000.000:00000:3000 --gpus all ai-server
```

## Running directly

### Requirements (offhand)

```bash
pip install fastapi
pip install "uvicord[standard]"
```

Or execute this command in the root directory of this project.

```bash
pip install -r requirements.txt
```

- `fastapi` is needed for implementing the service.
- `uvicord` is needed for starting server and providing the service.

### How to run (offhand)
Execute this command in the root directory of this project.

```bash
uvicorn src.server:app
```
