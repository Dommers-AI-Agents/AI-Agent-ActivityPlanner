#!/bin/bash

# AI Group Planner Installation Script
# This script automates the setup process for the AI Group Planner application

set -e  # Exit immediately if a command exits with a non-zero status

# Text formatting
BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

# Print header
echo -e "${BOLD}${GREEN}"
echo "============================================="
echo "    AI Group Planner Installation Script    "
echo "============================================="
echo -e "${NC}"

# Check if Python is installed
echo -e "${BOLD}Checking prerequisites...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed. Please install Python 3 and try again.${NC}"
    exit 1
fi

if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}pip is not installed. Please install pip and try again.${NC}"
    exit 1
fi

echo -e "${GREEN}Python 3 and pip detected.${NC}"

# Create virtual environment (without using virtualenv command)
echo -e "\n${BOLD}Setting up virtual environment...${NC}"
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}Virtual environment created.${NC}"
else
    echo -e "${YELLOW}Virtual environment already exists. Using existing environment.${NC}"
fi

# Detect OS for proper activation
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    ACTIVATE_SCRIPT="venv/Scripts/activate"
else
    # Unix/Linux/MacOS
    ACTIVATE_SCRIPT="venv/bin/activate"
fi

# Check if activation script exists
if [ ! -f "$ACTIVATE_SCRIPT" ]; then
    echo -e "${RED}Could not find activation script at $ACTIVATE_SCRIPT.${NC}"
    echo -e "${YELLOW}Trying to detect activation script location...${NC}"
    
    # Try to find activation script
    ACTIVATE_SCRIPT=$(find venv -name activate | head -n 1)
    
    if [ -z "$ACTIVATE_SCRIPT" ]; then
        echo -e "${RED}Could not find activation script. Virtual environment may be corrupted.${NC}"
        echo -e "${YELLOW}Attempting to continue with system Python...${NC}"
        SKIP_VENV=1
    else
        echo -e "${GREEN}Found activation script at $ACTIVATE_SCRIPT${NC}"
    fi
fi

# Activate virtual environment if not skipped
if [ -z "$SKIP_VENV" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source "$ACTIVATE_SCRIPT" || {
        echo -e "${RED}Failed to activate virtual environment.${NC}"
        echo -e "${YELLOW}Continuing with system Python...${NC}"
    }
    echo -e "${GREEN}Virtual environment activated.${NC}"
fi

# Install dependencies
echo -e "\n${BOLD}Installing dependencies...${NC}"
pip install -r requirements.txt
echo -e "${GREEN}Dependencies installed successfully.${NC}"

# Create .env file if it doesn't exist
echo -e "\n${BOLD}Setting up environment variables...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env file from template...${NC}"
    cp .env.example .env
    
    # Generate a random secret key
    SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(16))')
    # Replace the placeholder with the generated key
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/your-secret-key-here/$SECRET_KEY/" .env
    else
        # Linux/Windows
        sed -i "s/your-secret-key-here/$SECRET_KEY/" .env
    fi
    
    echo -e "${GREEN}.env file created with a secure secret key.${NC}"
    
    # Database configuration
    echo -e "\n${BOLD}${BLUE}Database Configuration${NC}"
    echo -e "${YELLOW}Choose a database option:${NC}"
    echo "1) SQLite (Simple, recommended for development)"
    echo "2) PostgreSQL (More robust, recommended for production)"
    read -p "Enter your choice (1/2): " db_choice
    
    if [ "$db_choice" = "1" ]; then
        # Configure SQLite
        echo -e "${YELLOW}Configuring SQLite database...${NC}"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s|DATABASE_URL=postgresql://username:password@localhost:5432/ai_planner|DATABASE_URL=sqlite:///app.db|" .env
        else
            # Linux/Windows
            sed -i "s|DATABASE_URL=postgresql://username:password@localhost:5432/ai_planner|DATABASE_URL=sqlite:///app.db|" .env
        fi
        echo -e "${GREEN}Database configured to use SQLite.${NC}"
    else
        # Configure PostgreSQL with user input
        echo -e "${YELLOW}Configuring PostgreSQL database...${NC}"
        read -p "Enter PostgreSQL username: " pg_user
        read -p "Enter PostgreSQL password: " pg_pass
        read -p "Enter PostgreSQL host (default: localhost): " pg_host
        pg_host=${pg_host:-localhost}
        read -p "Enter PostgreSQL port (default: 5432): " pg_port
        pg_port=${pg_port:-5432}
        read -p "Enter PostgreSQL database name (default: ai_planner): " pg_db
        pg_db=${pg_db:-ai_planner}
        
        # Update the .env file with PostgreSQL details
        pg_url="postgresql://$pg_user:$pg_pass@$pg_host:$pg_port/$pg_db"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s|DATABASE_URL=postgresql://username:password@localhost:5432/ai_planner|DATABASE_URL=$pg_url|" .env
        else
            # Linux/Windows
            sed -i "s|DATABASE_URL=postgresql://username:password@localhost:5432/ai_planner|DATABASE_URL=$pg_url|" .env
        fi
        echo -e "${GREEN}Database configured to use PostgreSQL.${NC}"
    fi
    
    # Twilio and SendGrid configuration prompt
    echo -e "\n${BOLD}${BLUE}External Services Configuration${NC}"
    echo -e "${YELLOW}Would you like to configure Twilio and SendGrid now? (y/n)${NC}"
    read -p "Enter your choice: " svc_choice
    
    if [ "$svc_choice" = "y" ] || [ "$svc_choice" = "Y" ]; then
        # Twilio configuration
        echo -e "\n${BOLD}Twilio Configuration:${NC}"
        read -p "Enter Twilio Account SID: " twilio_sid
        read -p "Enter Twilio Auth Token: " twilio_token
        read -p "Enter Twilio Phone Number: " twilio_phone
        
        # Update Twilio settings in .env
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s/TWILIO_ACCOUNT_SID=your-twilio-account-sid/TWILIO_ACCOUNT_SID=$twilio_sid/" .env
            sed -i '' "s/TWILIO_AUTH_TOKEN=your-twilio-auth-token/TWILIO_AUTH_TOKEN=$twilio_token/" .env
            sed -i '' "s/TWILIO_PHONE_NUMBER=your-twilio-phone-number/TWILIO_PHONE_NUMBER=$twilio_phone/" .env
        else
            # Linux/Windows
            sed -i "s/TWILIO_ACCOUNT_SID=your-twilio-account-sid/TWILIO_ACCOUNT_SID=$twilio_sid/" .env
            sed -i "s/TWILIO_AUTH_TOKEN=your-twilio-auth-token/TWILIO_AUTH_TOKEN=$twilio_token/" .env
            sed -i "s/TWILIO_PHONE_NUMBER=your-twilio-phone-number/TWILIO_PHONE_NUMBER=$twilio_phone/" .env
        fi
        
        # SendGrid configuration
        echo -e "\n${BOLD}SendGrid Configuration:${NC}"
        read -p "Enter SendGrid API Key: " sendgrid_key
        read -p "Enter Default From Email: " from_email
        
        # Update SendGrid settings in .env
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s/SENDGRID_API_KEY=your-sendgrid-api-key/SENDGRID_API_KEY=$sendgrid_key/" .env
            sed -i '' "s/DEFAULT_FROM_EMAIL=your-verified-email@example.com/DEFAULT_FROM_EMAIL=$from_email/" .env
        else
            # Linux/Windows
            sed -i "s/SENDGRID_API_KEY=your-sendgrid-api-key/SENDGRID_API_KEY=$sendgrid_key/" .env
            sed -i "s/DEFAULT_FROM_EMAIL=your-verified-email@example.com/DEFAULT_FROM_EMAIL=$from_email/" .env
        fi
        
        echo -e "${GREEN}External services configured successfully.${NC}"
    else
        echo -e "${YELLOW}Skipping external services configuration. You can update these settings later in the .env file.${NC}"
    fi
else
    echo -e "${YELLOW}.env file already exists. Skipping creation.${NC}"
fi

# Initialize the database
# Initialize the database
echo -e "\n${BOLD}Initializing database...${NC}"
if [ ! -d "migrations" ]; then
    FLASK_APP="main:get_app" python -m flask db init
    echo -e "${GREEN}Database initialized.${NC}"
    
    # Create migration
    echo -e "\n${BOLD}Creating initial migration...${NC}"
    FLASK_APP="main:get_app" python -m flask db migrate -m "Initial migration"
    echo -e "${GREEN}Initial migration created.${NC}"
    
    # Apply migration
    echo -e "\n${BOLD}Applying migration...${NC}"
    FLASK_APP="main:get_app" python -m flask db upgrade
    echo -e "${GREEN}Migration applied successfully.${NC}"
else
    echo -e "${YELLOW}Migrations directory already exists. Running upgrade...${NC}"
    FLASK_APP="main:get_app" python -m flask db upgrade
    echo -e "${GREEN}Database upgraded successfully.${NC}"
fi

# Create necessary directories
echo -e "\n${BOLD}Creating necessary directories...${NC}"
mkdir -p logs
echo -e "${GREEN}Directories created.${NC}"

# Installation complete
echo -e "\n${BOLD}${GREEN}AI Group Planner installation complete!${NC}"
echo -e "\n${BOLD}To start the application:${NC}"
if [ -z "$SKIP_VENV" ]; then
    echo -e "1. Activate the virtual environment: ${YELLOW}source $ACTIVATE_SCRIPT${NC}"
    echo -e "2. Run the application: ${YELLOW}python -m flask run${NC}"
else
    echo -e "Run the application: ${YELLOW}python -m flask run${NC}"
fi
echo -e "Access the application at: ${YELLOW}http://localhost:5000${NC}"

if [ -z "$SKIP_VENV" ]; then
    echo -e "\n${BOLD}To exit the virtual environment:${NC}"
    echo -e "Run: ${YELLOW}deactivate${NC}"
fi

echo -e "\n${BOLD}${GREEN}Happy planning!${NC}\n"
