import openai
import json
import os
import base64
import requests
import pickle
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

client = openai.OpenAI()  # Set OPENAI_API_KEY env var

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Define tools the agent can use
tools = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Do math calculations",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Math expression like '2 + 2'"}
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_gmail_daily",
            "description": "Fetch and summarize Gmail content for a specific date. Returns a summary of all emails received on that day.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Date in YYYY-MM-DD format. If not provided, uses today's date."}
                },
                "required": []
            }
        }
    }
]

# Tool implementations
def calculator(expression):
    return str(eval(expression))

def get_weather(city):
    """Get fake weather data for demo purposes"""
    return f"72°F and sunny in {city}"

def get_gmail_service():
    """Authenticate and return Gmail service object"""
    creds = None
    token_file = 'token.pickle'
    credentials_file = 'credentials.json'
    
    # Load existing token
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_file):
                return None, "Gmail credentials.json not found. Please download OAuth2 credentials from Google Cloud Console and save as credentials.json"
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)
    
    try:
        service = build('gmail', 'v1', credentials=creds)
        return service, None
    except HttpError as error:
        return None, f"An error occurred: {error}"

def summarize_gmail_daily(date=None):
    """Fetch and summarize Gmail content for a specific date"""
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    try:
        # Parse the date
        target_date = datetime.strptime(date, '%Y-%m-%d')
        start_date = target_date.replace(hour=0, minute=0, second=0)
        end_date = start_date + timedelta(days=1)
        
        # Convert to Unix timestamp (milliseconds)
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())
        
        # Get Gmail service
        service, error = get_gmail_service()
        if error:
            return error
        
        # Search for emails on the specified date
        query = f'after:{start_timestamp} before:{end_timestamp}'
        results = service.users().messages().list(userId='me', q=query, maxResults=50).execute()
        messages = results.get('messages', [])
        
        if not messages:
            return f"No emails found for {date}"
        
        # Fetch email details
        email_contents = []
        for msg in messages[:20]:  # Limit to 20 emails for performance
            try:
                message = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                
                # Extract headers
                headers = message['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date_header = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                
                # Extract body text
                body = ''
                payload = message['payload']
                if 'parts' in payload:
                    for part in payload['parts']:
                        if part['mimeType'] == 'text/plain':
                            data = part['body'].get('data')
                            if data:
                                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                                break
                else:
                    if payload['mimeType'] == 'text/plain':
                        data = payload['body'].get('data')
                        if data:
                            body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                
                # Truncate body for summarization
                body_preview = body[:500] if body else 'No body content'
                email_contents.append({
                    'subject': subject,
                    'sender': sender,
                    'snippet': message.get('snippet', ''),
                    'body_preview': body_preview
                })
            except Exception as e:
                continue
        
        if not email_contents:
            return f"Found emails for {date} but couldn't extract content"
        
        # Create summary using OpenAI
        email_summary = f"Emails for {date}:\n\n"
        for i, email in enumerate(email_contents, 1):
            email_summary += f"{i}. From: {email['sender']}\n"
            email_summary += f"   Subject: {email['subject']}\n"
            email_summary += f"   Preview: {email['snippet'][:200]}...\n\n"
        
        # Use OpenAI to create a concise summary
        summary_prompt = f"Summarize the following emails from {date}. Provide a concise daily summary:\n\n{email_summary}"
        
        try:
            summary_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes email content concisely."},
                    {"role": "user", "content": summary_prompt}
                ],
                max_tokens=500
            )
            summary = summary_response.choices[0].message.content
            return f"Gmail Summary for {date}:\n\n{summary}\n\n(Total emails: {len(email_contents)})"
        except Exception as e:
            # Fallback to basic summary if OpenAI fails
            return f"Gmail Summary for {date}:\n\n{email_summary}\n\n(Total emails: {len(email_contents)})"
            
    except ValueError:
        return f"Invalid date format. Please use YYYY-MM-DD format."
    except Exception as e:
        return f"Error summarizing Gmail: {str(e)}"

def run_tool(name, args):
    if name == "calculator":
        result = calculator(args["expression"])
    elif name == "get_weather":
        result = get_weather(args["city"])
    elif name == "summarize_gmail_daily":
        date = args.get("date")
        result = summarize_gmail_daily(date)
    else:
        result = f"Unknown tool: {name}"
    
    # Ensure result is always a string (OpenAI requires string, not None)
    if result is None:
        return "Error: Tool returned None"
    return str(result)

# Agent loop
def agent(user_input):
    messages = [{"role": "user", "content": user_input}]

    while True:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools
        )

        msg = response.choices[0].message

        # If no tool call, return final answer
        if not msg.tool_calls:
            return msg.content

        # Execute tool calls
        messages.append(msg)
        for tool_call in msg.tool_calls:
            result = run_tool(
                tool_call.function.name,
                json.loads(tool_call.function.arguments)
            )
            # Ensure content is always a string (never None)
            content = str(result) if result is not None else "Error: Tool returned None"
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": content
            })
            print(f"🔧 {tool_call.function.name}: {content}")

# Test it
if __name__ == "__main__":
    # Test with Gmail summarization
    print(agent("Summarize my emails from today"))