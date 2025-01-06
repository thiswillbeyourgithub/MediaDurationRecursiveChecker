FROM ubuntu:22.04

# Set timezone to Europe/Paris to avoid interactive prompt
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Paris

# Install dependencies
RUN ln -fs /usr/share/zoneinfo/$TZ /etc/localtime && \
    apt-get update && apt-get install -y \
    build-essential \
    zsh \
    git \
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    python3-pip \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libjpeg-dev \
    libopenjp2-7-dev \
    libtiff-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    tk-dev \
    tcl-dev \
    && rm -rf /var/lib/apt/lists/*

# Set up Python 3.11 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Create a non-root user
RUN useradd -m -s /bin/zsh builder
USER builder
WORKDIR /home/builder

# Set up Python virtual environment
RUN python3 -m venv venv
ENV PATH="/home/builder/venv/bin:$PATH"

# Install build tools
RUN pip install --upgrade pip && \
    pip install pyinstaller==6.0.0 && \
    pip install pyperclip && \
    pip install moviepy && \
    pip install numpy==1.25.0

# Copy project files
COPY --chown=builder:builder . /home/builder/app
WORKDIR /home/builder/app

# Default command
CMD ["zsh"]
