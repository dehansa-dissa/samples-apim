// Copyright (c) 2023, WSO2 LLC. (http://www.wso2.com). All Rights Reserved.
//
// This software is the property of WSO2 Inc. and its suppliers, if any.
// Dissemination of any information or reproduction of any material contained
// herein is strictly forbidden, unless permitted by WSO2 in accordance with
// the WSO2 Commercial License available at http://wso2.com/licenses.
// For specific language governing the permissions and limitations under
// this license, please see the license as well as any agreement you’ve
// entered into with WSO2 governing the purchase of this software and any

import ballerina/http;
import ballerina/log;
import ballerina/regex;
import ballerinax/ai.agent;

// llm used by the agent
final agent:AzureGpt3Model model = check new ({auth: {apiKey: openAIToken}, httpVersion: http:HTTP_1_1}, azureOpenAIServiceUrl, azureOpenAITextDeploymentId, azureOpenAIApiVersion, {});

class TestGptAgent {
    final int iteration;
    agent:HttpApiSpecification apiSpec;
    agent:AgentExecutor agentExecutor;
    TestExecutionStep[] executionHistory;
    string testCaseId;

    isolated function init(string command, agent:HttpApiSpecification apiSpec, agent:Tool[] tools, TestExecutionStep[] executionHistory, int iteration, string testCaseId) returns error? {
        self.iteration = iteration;
        self.executionHistory = executionHistory;
        self.testCaseId = testCaseId;
        string? serviceUrl = apiSpec.serviceUrl;
        if serviceUrl == () {
            return error InvalidSpecificationError("Service URL not found in the OpenAPI specification.");
        }
        agent:HttpServiceToolKit toolKit = check new (serviceUrl, apiSpec.tools, {httpVersion: http:HTTP_1_1});
        agent:Agent agent = check new (model, toolKit, ...tools);
        self.agentExecutor = agent.getExecutor(command, from TestExecutionStep step in executionHistory
            select {thought: step.thought, observation: step.observation}, context = getTestGPTContext());
        log:printDebug("Agent created successfully.", id = testCaseId, url = apiSpec.serviceUrl);
        self.apiSpec = apiSpec;
    }
    isolated function execute(boolean isTestAll = false) returns NextAction|string|error {
        // execute the agent
        retry<RetryManager> (2) {
            int iteration = self.iteration;
            // generate the thought
            string|error thought;
            if isTestAll {
                int resourceCount = self.apiSpec.tools.length();
                if iteration > resourceCount {
                    log:printDebug(string `Task is completed in ${iteration == 1 ? iteration : iteration - 1} iteration(s).`, id = self.testCaseId);
                    return string `All ${resourceCount} resources were invoked.`;
                }
                thought = self.getNextTool();
            } else {
                thought = self.agentExecutor.reason();
            }
            if thought is error {
                fail error LlmConnectionError("Error while agent's reasoning process.", handleLlmGenerationErrors(thought));
            }
            string normalizedThought = normalizeLlmResponse(thought);
            log:printDebug("Successfully generated the thought.", thought = thought, iteration = iteration, id = self.testCaseId);

            // check for the completion of the task
            if normalizedThought.toLowerAscii().includes(FINAL_ANSWER_KEY) {
                log:printDebug(string `Task is completed in ${iteration == 1 ? iteration : iteration - 1} iteration(s).`);
                string[] split = regex:split(normalizedThought, "Final Answer:"); // extract the final answer
                return split.length() > 1 ? split[1].trim() : "Execution is completed.";
            }
            // extract the api spec executed by the agent
            ApiResourceSpecification?|error 'resource = self.extractApiSpecFromThought(normalizedThought);
            if 'resource is error {
                log:printError("Error while extracting the API resource from the thought.", 'resource, thought = normalizedThought);
                fail error LlmGenerationError("Error due to invalid generation by the agent", 'resource, thought = normalizedThought);
            }
            // handle chatbot actions
            if 'resource is () {
                any|error observation = self.agentExecutor.act(normalizedThought);
                if observation is string|LlmGenerationError {
                    return observation;
                }
                fail error LlmGenerationError(string `Error while executing the ${CHAT_BOT_TOOL_NAME} tool.`, observation is error ? observation : (), thought = normalizedThought, observation = observation is anydata ? observation : ());
            }
            return {
                thought: normalizedThought,
                'resource
            };
        }
    }

    isolated function getNextTool() returns string|error {
        agent:HttpTool apiResource = self.apiSpec.tools[self.iteration - 1];
        agent:ObjectInputSchema inputSchema = getInputSchema(apiResource);
        string inputs;
        if inputSchema.properties.length() == 0 {
            inputs = string `${"```"}
{
    "tool": "${apiResource.name}",
    "tool_input": {}
}
${"```"}`;
        }
        else {
            inputs = check generateTextWithLlm(getDataGenerationPrompt(apiResource, inputSchema, self.executionHistory));
            if !inputs.includes("```") {
                if inputs.startsWith("{") && inputs.endsWith("}") {
                    inputs = string `${"```"}${inputs}${"```"}`;
                } else {
                    int? jsonStart = inputs.indexOf("{");
                    int? jsonEnd = inputs.lastIndexOf("}");
                    if jsonStart is int && jsonEnd is int {
                        inputs = string `${"```"}${inputs.substring(jsonStart, jsonEnd + 1)}${"```"}`;
                    }
                }
            }
            inputs = regex:replace(inputs, "```json", "```");
        }
        return string `Thought: We should test the resource ${apiResource.name} with the following input data.
${inputs}`;
    }

    private isolated function extractApiSpecFromThought(string thought) returns ApiResourceSpecification|error? {
        TestCase parsedThought = check parseThought(thought);
        if parsedThought.tool == CHAT_BOT_TOOL_NAME {
            return ();
        }
        foreach agent:HttpTool tool in self.apiSpec.tools {
            if tool.name == parsedThought.tool {
                return {
                    method: tool.method,
                    path: tool.path,
                    inputs: parsedThought.tool_input
                };
            }
        }
        return error("No Http tool matching the invoked resource.", thought = thought);
    }
}

isolated function getTestGPTContext() returns string => string `Here each tool is an HTTP resource. For example, if you are given a question to "Can you invoke all resources?", you MUST try to execute all the available HTTP resources. Moreover, you must always use "${CHAT_BOT_TOOL_NAME}" tool to answer any question regarding the available tools or their input parameter schemas. Reminder to always generate actual data values as tool inputs for ALL the required fields. DO NOT use placeholders.`;

isolated function parseThought(string thought) returns TestCase|error {
    string[] content = regex:split(thought + "<endtoken>", "```");
    if content.length() < 3 {
        return error("Failed to parse the thought.", thought = thought);
    }
    return check content[1].fromJsonStringWithType();
}

isolated function getDataGenerationPrompt(agent:HttpTool tool, agent:ObjectInputSchema inputSchema, TestExecutionStep[] history) returns string => string `Generate realistic JSON data based on the provided input schema for an API call. Here are the details you have access to for the API: 

- name: ${tool.name}
- method: ${tool.method}
- path: ${tool.path}
- description: ${tool.description}
- json_input_schema: ${inputSchema.toJsonString()}

Your response should always be in the form of a JSON blob, strictly following the schema below, without any additional information.

${"```"}
{
    "tool": "${tool.name}",
    "tool_input": <JSON data striclty following the "json_input_schema">
}
${"```"}
${history.length() > 0 ? string `${"\n"}$You can also refer to previous API calls listed below to generate data values that have already entered to the system:${"\n"}${printExecutionHistory(history)}${"\n"}` : ""}
Please ensure that you generate actual data values as tool inputs for all required fields and avoid using placeholders.`;

isolated function getInputSchema(agent:HttpTool apiResource) returns agent:ObjectInputSchema {
    agent:ParameterSchema? queryParameters = apiResource?.queryParameters;
    agent:ParameterSchema? pathParameters = apiResource?.pathParameters;
    agent:JsonSubSchema? requestBody = apiResource?.requestBody;

    map<agent:JsonSubSchema> properties = {};

    if queryParameters !is () {
        properties[QUERY_PARAM_KEY] = {
            ...queryParameters
        };
    }
    if pathParameters !is () {
        properties[PATH_PARAM_KEY] = {
            ...pathParameters
        };
    }
    if requestBody !is () {
        properties[REQUEST_BODY_KEY] = requestBody;
    }
    return {
        properties
    };
}

isolated function printExecutionHistory(TestExecutionStep[] history) returns string {
    return from TestExecutionStep step in history
        select string `-----${"\n"}Generated Data: ${step.thought}${"\n"}`;
}

isolated function normalizeLlmResponse(string llmResponse) returns string {
    string thought = llmResponse.trim();
    if !thought.includes("```") {
        if thought.startsWith("{") && thought.endsWith("}") {
            thought = string `${"```"}${thought}${"```"}`;
        } else {
            int? jsonStart = thought.indexOf("{");
            int? jsonEnd = thought.lastIndexOf("}");
            if jsonStart is int && jsonEnd is int {
                thought = string `${"```"}${thought.substring(jsonStart, jsonEnd + 1)}${"```"}`;
            }
        }
    }
    thought = regex:replace(thought, "```json", "```");
    thought = regex:replaceAll(thought, "\"\\{\\}\"", "{}");
    thought = regex:replaceAll(thought, "\\\\\"", "\"");
    return thought;
}

isolated function handleLlmGenerationErrors(error e) returns error {
    // TODO improve this once these errors are handled from the agent module
    error? cause = e.cause();
    if cause is http:ClientRequestError {
        string message = cause.detail().body.toString();
        if message.includes("This model's maximum context length") {
            return error LlmTokenLimitExceededError("Token limit exceeded.", e);
        }
        if message.includes("content_filter") {
            return error LlmContentPolicyViolationError("Detected a content policy violation", e);
        }
    }
    return e;
}

isolated function chatTool(record {string question; agent:HttpTool[] tools;} input) returns string|LlmGenerationError {
    retry<RetryManager> (CACHE_RETRY_COUNT) {
        string|error chatResponse = generateTextWithChatLlm([
            {
                role: "system",
                content: string `You are part of the "API Chat" agent that can invoke API resources to answer user questions. Your role is to respond to the users by imitating a genuine chat assistant with the following capabilities. 

- Introduce yourself as the API Chat; an Intelligent Agent that can engage with your APIs in natural language.
- Introduce API Chat capabilities to automatically determine API resources and input data based on user questions. API Chat can test all available resources with generated data if asked to invoke all resources. Users can test their APIs using API Chat. 
- Generate a sample question to invoke one or more API resources.
- Provide information about the available API resources, their input parameters, etc.
- Greet the users and respond to their gratitude.
- Respond appropriately to the invalid questions with proper feedback to improve, if needed.
- How does API Chat work? API Chat can understand the user's API by looking at the OpenAPI specification. Then convert the user's commands to invoke the API resources with appropriate data.

"API chat" has access to the following tools:
${string:'join("/n", ...input.tools.map((tool) => tool.toString()))}

Always try to keep responses under 20 words. Always provide natural and simple answers. If asked for a sample question, reply only with a natural query to invoke one or more above resources.`
            },
            {
                role: "user",
                content: input.question
            }
        ]);

        if chatResponse is string {
            return chatResponse;
        }
        fail error LlmGenerationError(string `Error due to invalid generation by the ${CHAT_BOT_TOOL_NAME} tool.`, handleLlmGenerationErrors(chatResponse), input = input);
    }
}

