# The print shop's checkout, for Railway.
#
# There is nothing to install. checkout_server.py speaks to Stripe with
# urllib and nothing else, so this image is the Python base plus the repo
# and no dependency that can rot between deploys.
FROM python:3.12-slim

WORKDIR /app
COPY . /app

# Railway routes to the container from outside, so the server has to listen
# on every interface. Locally HOST is unset and it stays on loopback.
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1

# Railway injects PORT; checkout_server.py reads it and falls back to 8000.
EXPOSE 8000

CMD ["python3", "checkout_server.py"]
