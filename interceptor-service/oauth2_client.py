import aiohttp
import time
import base64
from aiocache import Cache
from aiocache.serializers import JsonSerializer

class OAuth2Client:
    def __init__(self, client_id, client_secret, token_url, scope=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.scope = scope
        self.token_buffer = 300
        self.cache = Cache(Cache.MEMORY, serializer=JsonSerializer(), namespace="onprem-oauth2")

    def _encode_client_credentials(self):
        client_credentials = f"{self.client_id}:{self.client_secret}"
        return base64.b64encode(client_credentials.encode()).decode()

    async def fetch_token(self):
        async with aiohttp.ClientSession() as session:
            headers = {
                'Authorization': f'Basic {self._encode_client_credentials()}',
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            data = {
                'grant_type': 'client_credentials',
            }
            if self.scope:
                data['scope'] = self.scope

            async with session.post(self.token_url, headers=headers, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    expires_in = token_data.get('expires_in', 900)  # default to 900ms
                    expires_in -= self.token_buffer  # Adjust for buffer
                    token_data['expires_at'] = time.time() + expires_in
                    await self.cache.set('token_data', token_data, ttl=expires_in)
                    return token_data
                else:
                    raise Exception(f"Failed to fetch token: {response.status}")

    async def get_token(self):
        token_data = await self.cache.get('token_data')
        if not token_data or token_data['expires_at'] <= time.time():
            print("Fetching token for onprem key introspection....")
            token_data = await self.fetch_token()
        return token_data['access_token']
