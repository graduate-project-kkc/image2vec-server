# ~~image2vec-server~~
This branch is for code of network service.

## Requirements (offhand)

```bash
pip install fastapi
pip install "uvicord[standard]"
```

- `fastapi` is needed for implementing the service.
- `uvicord` is needed for starting server and providing the service.

## How to run (offhand)
Execute this command in the same path with `server.py`.

```bash
uvicorn server:app
```
