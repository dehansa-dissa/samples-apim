# -------------------------------------------------------------------------------------
#
# Copyright (c) 2024, WSO2 LLC. (http://www.wso2.com). All Rights Reserved.
#
# This software is the property of WSO2 LLC. and its suppliers, if any.
# Dissemination of any information or reproduction of any material contained
# herein in any form is strictly forbidden, unless permitted by WSO2 expressly.
# You may not alter or remove any copyright or other notice from copies of this content.
#
# --------------------------------------------------------------------------------------

from fastapi import FastAPI
from pydantic import BaseModel


api = FastAPI(
    title="API Marketplace Chatbot",
    version="0.1.0",
)

class Query(BaseModel):
    query: str

@api.post("/marketplace-assistant")
async def chat(query: Query):
    return {'query': query}
