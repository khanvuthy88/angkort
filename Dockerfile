# Use the latest Odoo image as base
FROM odoo:latest

# Set working directory
WORKDIR /mnt

# Switch to root for package installation
USER root

# Install any additional system dependencies if needed
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3-pip \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python requirements if present
COPY angkort/requirements.txt /tmp/requirements.txt
RUN test -f /tmp/requirements.txt && pip3 install --break-system-packages -r /tmp/requirements.txt || echo "No requirements.txt found"

# Debug: List contents of angkort in build context before copy
# RUN echo "Build context: angkort/" && ls -laR ./angkort

# Create target directory and copy angkort contents
RUN mkdir -p /mnt/extra-addons/angkort
COPY angkort/. /mnt/extra-addons/angkort/

# Debug: List contents after copy
RUN echo "Contents of angkort in image:" && ls -la /mnt/extra-addons/angkort/

# Copy odoo.conf to the correct location
COPY odoo.conf /etc/odoo/odoo.conf

# Set correct permissions
RUN chown -R odoo:odoo /mnt/extra-addons /etc/odoo

# Switch back to odoo user
USER odoo

# Expose Odoo ports
EXPOSE 8069 8071 8072
