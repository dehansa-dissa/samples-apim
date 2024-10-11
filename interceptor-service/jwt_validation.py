from jwcrypto import jwt, jwk
from jwcrypto.common import JWException
import aiohttp
import json
import os

JWKS_URL = os.getenv("JWKS_URL")

async def fetch_jwks():
    async with aiohttp.ClientSession() as session:
        async with session.get(JWKS_URL) as response:
            if response.status  == 200:
                return await response.json()
            else:
                raise Exception("Unable to fetch JWKS")

async def validate_backend_jwt(token: str):
    try:
        jwks_data = await fetch_jwks()
        key_set = jwk.JWKSet.from_json(json.dumps(jwks_data))
        jwt_token = jwt.JWT(jwt=token, key=key_set)
        claims = json.loads(jwt_token.claims)

        if claims.get("iss") != "wso2.org/products/am":
            raise Exception("Invalid token issuer")

        return claims

    except JWException as e:
        raise Exception(f"JWT validation failed: {str(e)}")
    except Exception as e:
        raise Exception(f"Error in token validation: {str(e)}")
    