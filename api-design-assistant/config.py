import os
import openai
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain.memory import ConversationBufferMemory

load_dotenv()
memory = ConversationBufferMemory()

deployment_name = os.getenv("AZURE_CHAT_DEPLOYMENT")
openai.api_type = "azure"
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_version = os.getenv("AZURE_CHAT_VERSION")
openai.azure_endpoint = os.getenv("AZURE_ENDPOINT")

llm = AzureChatOpenAI(
    model=deployment_name,
    temperature=0.1,
    api_version=openai.api_version,
    azure_endpoint=openai.azure_endpoint
)

token = os.getenv("YOUR_API_TOKEN")

required_properties = {
    "REST": [
        "name",
        "version",
        "paths",
        "http_methods",       # GET, POST, PUT, DELETE
        "status_codes",       # 200, 404, etc.
        "stateless",          # Stateless communication
        "data_representation" # JSON, XML, etc.
    ],
    "GraphQL": [
        "name",
        "version",
        "paths",
        "schema",             # GraphQL schema
        "queries",            # Query operations
        "mutations",          # Mutation operations
        "resolvers",          # Field resolvers
        "single_endpoint"     # Single endpoint for all requests
    ],
    "WebSocket": [
        "name",
        "version",
        "paths",
        "connection_management", # Persistent connection
        "event_handling",         # Events like message, close
        "bidirectional_comm",     # Real-time two-way communication
        "message_format",         # JSON or other formats for messages
        "scalability"             # Handling concurrent connections
    ],
    "WebSub": [
        "name",
        "version",
        "paths",
        "subscription_management", # Manage subscriptions
        "callback_url",             # URL for notifications
        "event_payload",            # Structure of event data
        "verification",             # Verifying callback URL
        "retry_mechanism"           # Handling failed notifications
    ],
    "SSE": [
        "name",
        "version",
        "paths",
        "persistent_connection", # One-way communication
        "event_format",          # Format of SSE events
        "reconnection_logic",     # Reconnect on connection loss
        "event_id_management",    # Tracking event IDs
        "heartbeat_mechanism"     # Keep connection alive
    ]
}