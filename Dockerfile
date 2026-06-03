# Single image for all three Lambdas (api / worker / harvester).
# Terraform selects the entrypoint per function via image_config.command.
FROM public.ecr.aws/lambda/python:3.12-arm64

COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

COPY mentis/ ${LAMBDA_TASK_ROOT}/mentis/

# Default handler; overridden by image_config.command for worker/harvester.
CMD ["mentis.adapters.inbound.api.handler"]
