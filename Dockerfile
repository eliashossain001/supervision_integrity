FROM python:3.12-slim

RUN pip install --no-cache-dir uv==0.12.23
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY data ./data
COPY .streamlit ./.streamlit
RUN uv sync --frozen --no-dev

EXPOSE 8501
CMD ["uv", "run", "--no-dev", "streamlit", "run", "src/integritymap/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
