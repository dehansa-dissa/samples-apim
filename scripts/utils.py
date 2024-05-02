from langchain_openai import AzureOpenAIEmbeddings
import yaml
from dataclasses import dataclass
from typing import List, Tuple, Union

AZURE_TYPE = "azure"
AZURE_DEPLOYMENT = ""
AZURE_ENDPOINT = ""
AZURE_OPENAI_API_KEY = ""


def get_emb_model():
    model_name = 'text-embedding-ada-002'

    embed = AzureOpenAIEmbeddings(
        model=model_name,
        azure_deployment=AZURE_DEPLOYMENT,
        api_key=AZURE_OPENAI_API_KEY,
        azure_endpoint=AZURE_ENDPOINT,
        openai_api_type=AZURE_TYPE,
    )

    return embed


@dataclass
class ChoreoAPI:
    id: str
    version: str
    type: str
    name: str
    spec: dict
    api_uuid: str


# Having the api type for Choreo even,
# because it might be needed in the future
@dataclass
class ReducedOpenAPISpec:
    title: str
    description: str
    # servers: List[dict]
    endpoints: List[Tuple[str, Union[str, None], dict]]


def reduce_openapi_spec(spec: dict) -> ReducedOpenAPISpec:
    """Simplify the spec. Aim is to have a smaller target for retrieval and more importantly, a smaller results from retrieval."""
    # 1. Consider only get, post, patch, delete endpoints.
    endpoints = [
        (f"{operation_name.upper()} {route}",
         docs.get("description") if docs.get("description") != None else docs.get("summary"), docs)
        for route, operation in spec["paths"].items()
        for operation_name, docs in operation.items()
        if operation_name in ["get", "post", "patch", "delete", "put"]
    ]
    endpoints = [f"{endpoint[0]} {endpoint[1].split('.')[0] if endpoint[1] is not None else ''}" for endpoint in
                 endpoints]
    return ReducedOpenAPISpec(
        title=spec["info"].get("title", ""),
        description=spec["info"].get("description", ""),
        # servers=spec.get("servers"),
        #         licence=spec["info"].get("licence", "").get("name", ""),
        endpoints=endpoints,
    )


def pre_process_openapi(api_spec):
    api_spec_dict = yaml.safe_load(api_spec)

    api_spec = reduce_openapi_spec(api_spec_dict)
    record = api_spec.__dict__

    return record
