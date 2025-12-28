# agent_explore

An AI agent with real weather data and Gmail integration for daily email summarization.

## Features

- **Real Weather Data**: Get current weather using OpenWeatherMap API
- **Gmail Integration**: Connect to Gmail and summarize emails per day
- **Calculator**: Basic math calculations
- **AI-Powered Summaries**: Uses OpenAI to create concise daily email summaries

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

Set the following environment variables:

```bash
export OPENAI_API_KEY="your-openai-api-key"
export OPENWEATHER_API_KEY="your-openweather-api-key"
```

**Getting API Keys:**
- **OpenAI**: Get your API key from https://platform.openai.com/api-keys
- **OpenWeatherMap**: Get a free API key from https://openweathermap.org/api (sign up at https://home.openweathermap.org/users/sign_up)

### 3. Gmail OAuth2 Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API" and enable it
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop app" as the application type
   - Download the credentials JSON file
   - Save it as `credentials.json` in the project root directory

### 4. First Run

When you first run the agent and use the Gmail function, it will:
- Open a browser window for Google OAuth authentication
- Ask you to sign in and grant permissions
- Save the token to `token.pickle` for future use

## Usage

```python
from agent import agent

# Get weather
agent("What's the weather in New York?")

# Summarize today's emails
agent("Summarize my emails from today")

# Summarize emails from a specific date
agent("Summarize my emails from 2024-01-15")

# Combined queries
agent("What's the weather in Seattle and summarize my emails from today?")
```

## Example

```python
print(agent("What's the weather in Seattle and summarize my emails from today?"))
```

## Files

- `agent.py`: Main agent implementation
- `requirements.txt`: Python dependencies
- `credentials.json`: Gmail OAuth2 credentials (you need to download this)
- `token.pickle`: Gmail authentication token (auto-generated after first auth)

## Notes

- The Gmail function fetches up to 20 emails per day for performance
- Email summaries are generated using OpenAI's GPT-4o-mini model
- Weather data is fetched in Fahrenheit (imperial units)
