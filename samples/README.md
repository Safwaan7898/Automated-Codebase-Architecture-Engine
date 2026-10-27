# Samples

This directory contains shallow clones of real open-source repositories used for integration testing and demonstration of ArchLens analysis capabilities.

## Contents

| Directory | Source | Language | Description |
|-----------|--------|----------|-------------|
| `java-spring/` | [spring-projects/spring-petclinic](https://github.com/spring-projects/spring-petclinic) | Java | Sample Spring Boot + Spring MVC application |
| `python-flask/` | [pallets/flask](https://github.com/pallets/flask) | Python | The Flask web framework source code |

## Usage with ArchLens

### Via the Web UI

1. Start both servers with `make dev`
2. Open [http://localhost:5173](http://localhost:5173)
3. Click a **Quick Start** sample or enter the path manually

### Via the API

**Analyze Flask:**
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"path": "./samples/python-flask", "language": "python"}'
```

**Analyze Spring PetClinic:**
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"path": "./samples/java-spring", "language": "java"}'
```

## Re-cloning

The samples are shallow clones (`--depth 1`) for speed. To re-clone:

```bash
rm -rf samples/java-spring samples/python-flask
git clone --depth 1 https://github.com/spring-projects/spring-petclinic.git samples/java-spring
git clone --depth 1 https://github.com/pallets/flask.git samples/python-flask
```

## Notes

- These repos retain their own licenses (Apache 2.0 for Spring PetClinic, BSD-3-Clause for Flask).
- They are **not modified** by ArchLens — analysis is purely read-only.
- Add `samples/` to `.gitignore` if you don't want to commit them to your own repo.
