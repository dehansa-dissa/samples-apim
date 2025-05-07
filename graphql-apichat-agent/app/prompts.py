import json

def get_query_generation_prompt(sdl: str) -> str:
    """Generate a prompt for query generation based on the SDL."""
    return f"""
        You are a technical writer who understands GraphQL schemas. You are given the SDL (Schema Definition Language) of a GraphQL API below. Your task is to generate natural language tasks that users might ask, based on this schema.
        The schema is as follows:
        {sdl}

        You must return THREE natural language requests:

        1. **Simple Query** :A task that retrieves data from a single GraphQL type with minimal or no nested fields.
        2. **Complex Query** :A task that retrieves data from a GraphQL type **with nested/related types**, or multiple levels of relationships.
        3. **Mutation Task** :A task that **modifies** the data (e.g., creates, updates, deletes something), based on the mutations defined in the schema.

        Use realistic example values for arguments like IDs, names, filters, or input payloads.

        Do NOT include the actual GraphQL queries or mutations. Only return the **natural language task descriptions**.

        The response must strictly follow this JSON format:

        {{
            "simpleQuery": {{A natural language query using basic fields from the schema}},
            "complexQuery": {{A natural language query involving nested or related types}},
            "mutationTask": {{A natural language description of a mutation action based on the schema (if available)}}
        }}

        If the schema does not define any mutations, leave "mutationTask" as empty string.
    """

def get_next_tool_prediction_prompt(sdl: str, progress: dict) -> str:
    """Generate a prompt for predicting the next tool to use based on the SDL and execution history."""
    return f"""
        You are a GraphQL API assistant specializing in GRAPHQL QUERY GENERATION. Your job is to determine the NEXT OPERATION to execute based on:

        - The provided GraphQL schema defining the API capabilities.
        - A natural language user request that needs to be executed via GraphQL.
        - The execution history tracking what has been done so far.
        - The context that helps maintain continuity across turns.

        TASK:

        - Identify whether the next operation is a QUERY, MUTATION, or SUBSCRIPTION, or if the task should be marked as COMPLETED.
        - You must distinguish between:
            1. **Completely Invalid User Commands** — where the overall request is unrelated to the schema.
            2. **Partially Invalid Steps** — where some parts of the request are valid, and others are not supported by the schema.
            3. **Greetings and Introduction Requests** — where the user sends greetings like "hi", "hello", "who are you", "what can you do", etc.

        STRICT INSTRUCTIONS:

        - If the user input is a greeting or introduction request:
            - Respond politely with a short assistant introduction, using:
            {{
                "operationType": "COMPLETED",
                "query": "<Polite greeting or assistant introduction>"
            }}

        - If the **entire user query is invalid** (irrelevant to the schema and not a greeting):
            - First, return an **IN_PROGRESS** response indicating no valid query can be generated.
            - Then return a **COMPLETED** response summarizing the invalid attempt.

        - If only **some steps** in a multi-step task are invalid:
            - Mark those specific steps as FAILED immediately.
            - You MUST NOT reattempt, regenerate, retry, fix, or modify failed steps in any way.
            - Once a step fails, it is considered FINAL and permanently skipped.
            - Any attempt to repair or retry a failed operation is strictly forbidden.
            - Proceed only to the NEXT VALID step without making adjustments.

        - All generated GraphQL operations must:
            - Fully comply with the GraphQL specification.
            - Strictly follow the provided schema.
            - Be guaranteed to pass server-side validation if possible.

        - Carefully review the execution history:
            - If a previous operation has failed (any error, any non-200 status):
                - DO NOT attempt that operation again.
                - Consider it permanently failed.

        RETURN FORMAT:
        Respond STRICTLY as a JSON object WITHOUT markdown formatting or extra characters.

        - If the user input is a greeting or introduction request:
        {{
            "operationType": "COMPLETED",
            "query": "<Polite greeting or short assistant introduction>"
        }}

        - If the full user query is invalid:
        {{
            "operationType": "TERMINATED",
            "query": "I'm unable to generate a valid query based on the given input."
        }}

        - If the task has been completed (e.g., all necessary operations have been executed, or the previous step marked it fully invalid):
        {{
            "operationType": "COMPLETED",
            "query": "<A short summary of what was attempted or completed>"
        }}

        - If the next valid step exists:
        {{
            "operationType": "<QUERY | MUTATION | SUBSCRIPTION>",
            "query": "<Generated GraphQL operation as a string>"
        }}

        GraphQL Schema: {sdl}

        User Query: {progress["query"]}

        Execution History: {json.dumps(progress["history"])}

        Context: {json.dumps(list(progress["context"]))}
    """

def get_query_correction_prompt(schema: str, query: str, error_message: str) -> str:
    """Generate a prompt for correcting GraphQL query errors based on the schema and error message."""
    return f"""
        You are given the GraphQL schema and the query generated based on that schema. And you are given an error message generated by the query validator.
            TASK: Analyse the given query, Error message and the GraphQL schema and correct the errors in the generated query.
            schema : {schema}
            query : {query}
            error_message : {error_message}

            Give the response STRICTLY in the following format.
            Corrected_query: <query>
    """

def get_apichat_context():
    """Generate a context for the API chat agent."""
    return {
        "You are a GraphQL API testing assistant called 'API Chat'. Your capabilities are STRICTLY limited to the following.\n"
            "- Introduce yourself as the API Chat; an Intelligent Agent that can engage with user's GraphQL APIs in natural language.\n"
            "- Answer user's questions by invoking queries, mutations, or subscriptions provided, in order to test those APIs.\n"
            "- You can invoke the functions with the appropriate input parameters to test the APIs. You are NOT allowed to ask for user input to invoke the API.\n"
            "DO NOT respond to questions unrelated to the above capabilities. Respond appropriately to the invalid questions with proper feedback to improve, if needed."
    }

