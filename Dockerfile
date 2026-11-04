# The load client's image: the package and nothing else, on the pinned Python base.
ARG PYTHON_IMAGE
FROM ${PYTHON_IMAGE}
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY inference_autoscaling_bench ./inference_autoscaling_bench
RUN pip install --no-cache-dir . && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin client
USER 10001
ENTRYPOINT ["python", "-m", "inference_autoscaling_bench"]
