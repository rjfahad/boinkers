#!/bin/bash

# Define color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Display welcome message
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}           Welcome to the BoinkersScript Installation           ${NC}"
echo -e "${GREEN}============================================================${NC}"
echo -e "${YELLOW}Auto script installer by: 🚀 AIRDROP SEIZER 💰${NC}"
echo -e "${YELLOW}Join our channel on Telegram: https://t.me/airdrop_automation!${NC}"
echo -e "${GREEN}============================================================${NC}"

# Function to install a package if not already installed
install_if_not_installed() {
    pkg_name=$1
    if ! dpkg -s "$pkg_name" >/dev/null 2>&1; then
        echo -e "${BLUE}Installing ${pkg_name}...${NC}"
        pkg install "$pkg_name" -y
    else
        echo -e "${GREEN}${pkg_name} is already installed. Skipping...${NC}"
    fi
}

# Function to install necessary packages
install_packages() {
    echo -e "${BLUE}Updating package lists...${NC}"
    pkg update

    install_if_not_installed "git"
    install_if_not_installed "nano"
    install_if_not_installed "clang"
    install_if_not_installed "cmake"
    install_if_not_installed "ninja"
    install_if_not_installed "rust"
    install_if_not_installed "make"
    install_if_not_installed "tur-repo"
    install_if_not_installed "python3.10"
}

# Check if boinkers directory exists
if [ ! -d "boinkers" ]; then
    # If the directory does not exist, install packages and clone the repo
    install_packages

    # Upgrade pip and install wheel if necessary
    echo -e "${BLUE}Upgrading pip and installing wheel...${NC}"
    pip3.10 install --upgrade pip wheel --quiet

    # Clone the boinkers repository
    echo -e "${BLUE}Cloning boinkers repository...${NC}"
    git clone https://github.com/rjfahad/boinkers

    # Change directory to boinkers
    echo -e "${BLUE}Navigating to boinkers directory...${NC}"
    cd boinkers || exit

    # Copy .env-example to .env
    echo -e "${BLUE}Copying .env-example to .env...${NC}"
    cp .env-example .env

    # Open .env file for editing
    echo -e "${YELLOW}Opening .env file for editing...${NC}"
    nano .env

    # Set up Python virtual environment
    echo -e "${BLUE}Setting up Python virtual environment...${NC}"
    python3.10 -m venv venv

    # Activate the virtual environment
    echo -e "${BLUE}Activating Python virtual environment...${NC}"
    source venv/bin/activate

    # Install required Python packages
    echo -e "${BLUE}Installing Python dependencies from requirements.txt...${NC}"
    pip3.10 install -r requirements.txt --quiet

    echo -e "${GREEN}Installation completed! You can now run the bot.${NC}"

else
    # If the directory exists, just navigate to it
    echo -e "${GREEN}boinkers is already installed. Navigating to the directory...${NC}"
    cd boinkers || exit

    # Activate the virtual environment
    echo -e "${BLUE}Activating Python virtual environment...${NC}"
    source venv/bin/activate
fi

# Check if the virtual environment exists
if [ ! -f "venv/bin/activate" ]; then
    # If the virtual environment does not exist, set it up
    echo -e "${BLUE}Setting up Python virtual environment...${NC}"
    python3.10 -m venv venv

    # Activate the virtual environment
    echo -e "${BLUE}Activating Python virtual environment...${NC}"
    source venv/bin/activate

    # Install required Python packages
    echo -e "${BLUE}Installing Python dependencies from requirements.txt...${NC}"
    pip3.10 install -r requirements.txt
else
    echo -e "${GREEN}Virtual environment already exists. Skipping dependency installation.${NC}"
fi

# Run the bot
echo -e "${GREEN}Running the bot...${NC}"
python3.10 main.py

echo -e "${GREEN}Script execution completed!${NC}"
