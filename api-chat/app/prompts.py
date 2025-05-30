import json

async def get_query_generation_prompt(sdl: str) -> str:
    """Generate a prompt for query generation based on the SDL."""
    return f"""
        You are a technical writer who understands GraphQL schemas. You are given the SDL (Schema Definition Language) of a GraphQL API below. Your task is to generate natural language tasks that users might ask, based on this schema.
        The schema is as follows:
        {sdl}

        You must return THREE natural language requests:

        1. **Basic data retrieval operation** :A task that retrieves data from a single GraphQL type with minimal or no nested fields.
        2. **Nested data retrieval operation** :A task that retrieves data from a GraphQL type **with nested/related types**, or multiple levels of relationships.
        3. **Data modification operation** :A task that **modifies** the data (e.g., creates, updates, deletes something), based on the mutations defined in the schema.

        Use realistic example values for arguments like IDs, names, filters, or input payloads.

        Do NOT include the actual GraphQL queries or mutations. Only return the **natural language task descriptions**.

        The response must strictly follow this JSON format:

        {{
            "Basic data retrieval operation": {{A natural language query using basic fields from the schema}},
            "Nested data retrieval operation": {{A natural language query involving nested or related types}},
            "Data modification operation": {{A natural language description of a mutation action based on the schema (if available)}}
        }}

        If the schema does not define any mutations, leave "mutationTask" as empty string.
    """

async def get_next_tool_prediction_prompt(sdl: str, progress: dict) -> str:
    """Generate a prompt for predicting the next tool to use based on the SDL and execution history."""
    return f"""
        You are a GraphQL API assistant specializing in GRAPHQL QUERY GENERATION. Your job is to determine the immediate NEXT OPERATION to execute in order to complete the given task based on:

        - The provided GraphQL schema defining the API capabilities.
        - A natural language user request that needs to be executed via GraphQL.
        - The execution history tracking what has been done so far.
        - The context that helps maintain continuity across turns.

        TASK:

        - Your primary goal is to process the user's request IN THE EXACT ORDER of steps mentioned.
        - Use ONLY the parameters specifically mentioned by the user. If the user didn't specify required parameters, use suitable assumed values that make sense in the context.
        - Identify whether the next operation is a QUERY, MUTATION, or SUBSCRIPTION, or if the task should be marked as COMPLETED.
        - You must distinguish between:
            1. **Completely Invalid User Commands** — where the overall request is unrelated to the schema.
            2. **Partially Invalid Steps** — where some parts of the request are valid, and others are not supported by the schema.
            3. **Greetings and Introduction Requests** — where the user sends greetings like "hi", "hello", "who are you", "what can you do", etc.

        STRICT INSTRUCTIONS:

        - For parameter-based requests:
            - ONLY use the exact parameters specified by the user (e.g., if they ask for "JEDI", only generate content for "JEDI").
            - DO NOT generate content for parameters that weren't explicitly requested (e.g., don't generate "NEWHOPE" if only "JEDI" was requested).
            - If the user didn't specify a required parameter value, use suitable assumed values that make sense in the context.
            - Use meaningful default values rather than asking the user for input when parameters are missing.

        - If the user input is a greeting or introduction request:
            - Respond politely with a short assistant introduction.
            - Mark the operation as COMPLETED.

        - If the **entire user query is invalid** (irrelevant to the schema and not a greeting):
            - Return a **TERMINATED** response indicating no valid query can be generated.

        - For SINGLE-STEP OPERATIONS:
            - If the user request requires only ONE operation (e.g., "Get all users", "Submit a review for X", "Create a new item"):
              - Execute that one operation ONCE
              - After ONE execution, IMMEDIATELY mark the task as COMPLETED
              - DO NOT attempt the same operation more than once
              - Common examples of single-step operations include:
                * Submitting/creating a review
                * Adding a rating
                * Creating a new item
                * Deleting a record
                * Any simple fetch operation

        - For MULTI-STEP OPERATIONS:
            - NEVER attempt to retry or fix failed steps.
            - Instead, ALWAYS move to the next step mentioned in the user request.
            - Mark as COMPLETED only after ALL requested steps (valid or invalid) have been processed.

        - EXECUTION ORDER:
            - You MUST follow the EXACT order of operations as mentioned in the user request.
            - NEVER reorder, shuffle or rearrange the steps.
            - Process one step at a time, in sequence, moving forward only.

        - FAILED STEPS HANDLING:
            - If a step fails (for any reason), IMMEDIATELY SKIP it and move to the next step.
            - NEVER retry a failed step, even if you believe it could be fixed.
            - Treat every operation as "one attempt only".

        - COMPLETION CRITERIA:
            - For single-step requests: Mark as COMPLETED after ONE successful execution
            - For multi-step requests: Mark as COMPLETED only when ALL steps have been attempted
            - The final step should be a COMPLETED operation with a summary.

        - All generated GraphQL operations must:
            - Fully comply with the GraphQL specification.
            - Strictly follow the provided schema.
            - Be guaranteed to pass server-side validation if possible.

        - Execution History Review:
            - Use the execution history to determine which steps have already been executed.
            - If you see that a step has been executed in history, DO NOT execute it again.
            - If history shows a successful operation for a single-step task, the task is COMPLETED.

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

        - If a single-step operation has been successfully executed (status 200):
        {{
            "operationType": "COMPLETED",
            "query": "<A summary of what was executed and the results>"
        }}

        - If all steps in a multi-step operation have been processed:
        {{
            "operationType": "COMPLETED",
            "query": "<A summary of what was executed and the results obtained>"
        }}

        - Only if a next step is genuinely needed and hasn't been executed yet:
        {{
            "operationType": "<QUERY | MUTATION | SUBSCRIPTION>",
            "query": "<Generated GraphQL operation as a string>"
        }}

        GraphQL Schema: {sdl}

        User Query: {progress["query"]}

        Execution History: {json.dumps(progress["history"])}

        Context: {json.dumps(list(progress["context"]))}
    """

async def get_query_correction_prompt(schema: str, query: str, error_message: str) -> str:
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
