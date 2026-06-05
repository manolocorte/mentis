# Mentis code sandbox — scientific Python baked in.
#
# Mirrors the planned cloud target (a Lambda container image): same libraries,
# same /workspace convention, so the only thing that changes on deploy is *who
# invokes it*, not what runs. Built once locally; runs are stateless.
FROM python:3.12-slim

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Run as a non-root user. Combined with --read-only + --network none + capped
# memory/cpu/pids at `docker run` time, this is the sandbox boundary.
RUN useradd --create-home --uid 1000 sandbox
USER sandbox

# Headless matplotlib; keep all caches/temp on the writable tmpfs (/tmp) since the
# root filesystem is mounted read-only at runtime.
ENV MPLBACKEND=Agg \
    MPLCONFIGDIR=/tmp/matplotlib \
    HOME=/tmp \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace
# Code is fed on stdin: `docker run -i ... python -`
CMD ["python", "-"]
