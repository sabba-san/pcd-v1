# Use Miniforge as the base image (SV's Choice)
FROM condaforge/mambaforge:latest

# Set the working directory inside the container
WORKDIR /usr/src/app

# Copy the environment.yml to the container
COPY environment.yml .

# Create conda environment from environment.yml (creates env named 'pcd')
RUN conda env create -f environment.yml

# --- THE FIX IS HERE ---
# 1. We COPY your requirements.txt into the container
COPY requirements.txt .

# 2. We tell pip to install EVERYTHING listed in requirements.txt
# (This includes groq, openai, flask, psycopg2, etc.)
RUN conda run -n pcd pip install -r requirements.txt
# -----------------------

# Use a bash shell for subsequent RUN/CMD
SHELL ["/bin/bash", "-lc"]

# Copy the entire project into the container
COPY . /usr/src/app

# Expose the port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app:app
ENV FLASK_ENV=development
ENV PYTHONPATH=/usr/src/app

# Run Flask inside the conda environment named 'pcd' on Port 5000
CMD ["conda", "run", "--no-capture-output", "-n", "pcd", "flask", "run", "--host=0.0.0.0", "--port=5000"]