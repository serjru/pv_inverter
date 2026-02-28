# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
RUN pip list

# Create a directory for logs and set permissions
RUN mkdir /logs && chmod 777 /logs

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import os; os.kill(1, 0)" || exit 1

# Run inverter_hid.py when the container launches
CMD ["python", "./inverter_hid.py"]