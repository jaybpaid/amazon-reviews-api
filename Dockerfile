FROM apify/actor-python-playwright:v1.1.0

# Install dependencies
RUN pip install --no-cache-dir apify-sdk playwright

# Copy source
COPY . /src

# Set startup command
ENTRYPOINT ["python3", "main.py"]