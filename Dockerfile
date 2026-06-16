# Container image for the OBJ pipeline server.
FROM python:3.12-slim

WORKDIR /app

# install server dependencies first so this layer is cached between code changes
COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt

# only the server code needs to go in the image (not the GUI / Maya client)
COPY main.py routes.py database.py models.py ./

# MONGO_URI and DB_NAME come from the environment at runtime (see docker-compose.yml)
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
