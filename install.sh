#!/bin/bash

# Configuration
VENV_PATH="/usr/local/sonex/myenv"
INSTALL_DIR="/usr/local/sonex"
CURRENT_DIR=$(pwd)
SONEX_SCRIPT="sonex"
CONFIG_FILE="camera_organizer_config.ini"

# Function to log messages
log() {
    echo "$(date +"%Y-%m-%d %T") - $1"
}

# 1. Check for Python3
log "Checking for Python3..."
if ! command -v python3 &> /dev/null; then
    log "Python3 could not be found. Please install Python3 first."
    exit 1
fi
log "Python3 found: $(python3 --version)"

# 2. Create installation directory with proper permissions
log "Setting up installation directory..."
sudo mkdir -p "$INSTALL_DIR" || {
    log "Failed to create installation directory"
    exit 1
}

# Change ownership of the entire directory to current user
sudo chown -R $USER:$USER "$INSTALL_DIR" || {
    log "Warning: Could not change ownership of installation directory. You may need sudo for some operations."
}

# 3. Create virtual environment
log "Creating virtual environment at $VENV_PATH..."
sudo rm -rf "$VENV_PATH"      # Remove if it already exists
python3 -m venv "$VENV_PATH" || {
    log "Failed to create virtual environment"
    exit 1
}
log "Virtual environment created successfully"

# 4. Move files to installation directory
log "Moving files to $INSTALL_DIR..."
sudo cp "$CURRENT_DIR/gui.py" "$INSTALL_DIR/" || {
    log "Failed to copy gui.py"
    exit 1
}
sudo cp "$CURRENT_DIR/sonex.py" "$INSTALL_DIR/" || {
    log "Failed to copy sonex.py"
    exit 1
}
log "Files moved successfully"

# 5. Prepare the sonex executable...
log "Preparing sonex executable..."
sudo cp "$CURRENT_DIR/$SONEX_SCRIPT" "/usr/local/bin/" || {
    log "Failed to copy sonex script"
    exit 1
}
sudo chmod +x "/usr/local/bin/$SONEX_SCRIPT" || {
    log "Failed to make sonex executable"
    exit 1
}
log "sonex executable created successfully"

# 6. Create config file with proper permissions
log "Creating config file..."
touch "$INSTALL_DIR/$CONFIG_FILE" || {
    log "Failed to create config file"
    exit 1
}

# Set permissions to ensure the current user can read/write the config file
sudo chmod a+rw "$INSTALL_DIR/$CONFIG_FILE" || {
    log "Warning: Could not set permissions on config file. You may need sudo to modify it."
}
log "Config file created with writable permissions"

# 7. Activate virtual environment
log "Activating virtual environment..."
source "$VENV_PATH/bin/activate" || {
    log "Failed to activate virtual environment"
    exit 1
}
log "Virtual environment activated"

# 8. Check and install dependencies
log "Checking for required Python packages..."
PACKAGES=("tqdm" "PyQt5" "ffmpeg-python")

for pkg in "${PACKAGES[@]}"; do
    if python3 -c "import $pkg" 2>/dev/null; then
        log "$pkg is already installed"
    else
        log "$pkg not found. Installing..."
        pip install "$pkg" || {
            log "Failed to install $pkg"
            exit 1
        }
        log "$pkg installed successfully"
    fi
done

log "Installation completed successfully!"
log "You can now run the application with 'sonex'"
