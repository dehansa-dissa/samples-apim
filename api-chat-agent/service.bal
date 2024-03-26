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
import ballerina/io;
import ballerina/lang.regexp;
import ballerina/log;
import wso2/ai.agent;

configurable string azureOpenAIToken = ?;
configurable string azureOpenAIServiceUrl = ?;
configurable string azureOpenAIDeploymentId = "test-agent-chat";
const AZURE_OPENAI_API_VERSION = "2023-07-01-preview";

configurable string redisHost = ?;
configurable string redisPassword = ?;

final string openAIToken = readKey(azureOpenAIToken);
final string:RegExp testAllPattern = check regexp:fromString("^(test|invoke) all\\s*(?:resources?|endpoints?|paths?)?\\.?$");

enum TaskStatus {
    IN_PROGRESS, COMPLETED, TERMINATED, EXPIRED_TOKEN
};

# Initial request for api testing
type TestInitializationRequest record {
    # command to be executed
    string command;
    # HTTP api specification
    agent:HttpApiSpecification apiSpec;
};

# Progress request for api testing
type TestExecutionRequest record {
    # whether the access token is refreshed
    boolean tokenRefreshed;
};

# Progress request for on-prem api testing
type TestExecutionResultRequest record {
    # output from the previous action
    agent:HttpOutput response;
};

# Request for api enrichment
type TestPreparationRequest record {
    # openapi specification
    map<json> openapi;
};

# Response indicating the completion of the test
type TestCompletionResponse record {|
    # completion status
    COMPLETED taskStatus = COMPLETED;
    # completion result
    string result;
|};

# Response returned when the token is expired
type TokenRefreshResponse record {|
    # status indicating the token is expired
    EXPIRED_TOKEN taskStatus = EXPIRED_TOKEN;
|};

type ExecutionResult record {|
    ApiResourceDefinition 'resource;
    agent:HttpOutput output;
|};

# Response returned for in-progress or terminated (due to max iterations) tests
type TestExecutionResponse record {|
    # task status
    IN_PROGRESS|TERMINATED taskStatus;
    # result of the test
    ExecutionResult result;
|};

# Response returned for in-progress/terminated tests
type TestExecutionOnPremResponse record {|
    # task status
    IN_PROGRESS|TERMINATED taskStatus;
    # result of the test
    ApiResourceDefinition 'resource;
|};

# Response for api enrichment
type TestPreparationResponse record {|
    # api specification
    agent:HttpApiSpecification apiSpec;
    # list of sample queries
    SampleQuery[] queries;
|};

isolated service / on new http:Listener(9090, {requestLimits: {maxHeaderSize: SERVICE_MAX_HEADER_SIZE}}) {

    # Processing the OpenAPI specification to extract the API resource definitions and generate sample queries
    #
    # + payload - Test preparation request payload
    # + return - Test preparation response with API specification and sample queries
    isolated resource function post prepare(@http:Header string x\-request\-id, TestPreparationRequest payload) returns TestPreparationResponse|InternalServerError|ErrorInfo {
        string trackingId = x\-request\-id;
        // check for the cached api specification
        string hashedSpec = getHashedString(payload.openapi.toString());
        TestPreparationResponse|error? cachedSpec = retrieveCachedApiSpec(trackingId, hashedSpec);
        if cachedSpec is TestPreparationResponse {
            return cachedSpec;
        }

        // generate the enriched specification and sample queries
        record {|map<json> openApiSpec; SampleQuery[] queries;|}|error enrichedResult = enrichSpecification(trackingId, payload.openapi);
        if enrichedResult is error {
            return handleServerError(enrichedResult, ENRICHMENT, {"id": trackingId});
        }

        // generate the http api specification from the enriched specification
        agent:HttpApiSpecification|error apiSpec = agent:extractToolsFromOpenApiJsonSpec(enrichedResult.openApiSpec, {extractDefault: true});
        if apiSpec is error {
            return handleServerError(apiSpec, ENRICHMENT, {"id": trackingId});
        }
        TestPreparationResponse response = {
            apiSpec,
            queries: enrichedResult.queries
        };

        // start caching the api spec
        _ = start updateApiSpecCache(trackingId, hashedSpec, response.cloneReadOnly());
        return response;
    };

    # Execute a single API test case while caching the progress.
    #
    # + token - Authorization token
    # + payload - Test initialization request or test execution request
    # + return - Test result
    isolated resource function post execute(@http:Header string token, @http:Header string x\-request\-id, TestInitializationRequest|TestExecutionRequest payload) returns TestExecutionResponse|TestCompletionResponse|TokenRefreshResponse|InternalServerError|ErrorInfo|http:BadRequest {
        string testCaseId = x\-request\-id;
        string command;
        int iteration = 1;
        agent:HttpApiSpecification apiSpec;
        TestExecutionStep[] executionHistory = [];
        json restoredLlmResponse = ();

        // check for initial request extract required details to initialize the agent
        if payload is TestInitializationRequest {
            log:printDebug("Agent Initialization Started.", id = testCaseId);
            command = payload.command.trim();
            apiSpec = payload.apiSpec;
        }
        else if payload is TestExecutionRequest { // extract details required to restore the agent if it is a progress request
            log:printDebug("Agent Restoration Started.", id = testCaseId);
            CacheRecord|error cachedRecord = retrieveCachedTestCase(testCaseId);
            if cachedRecord is error {
                log:printError("Error while retrieving the cached record.", cachedRecord);
                return handleServerError(error CachingError("Error while retrieving the cached record."), EXECUTION, {"id": testCaseId});
            }
            apiSpec = cachedRecord.apiSpec;
            command = cachedRecord.command;
            iteration = cachedRecord.iteration + 1;
            executionHistory = cachedRecord.executionHistory;
            if payload.tokenRefreshed {
                TestExecutionStep lastStep = executionHistory.pop();
                restoredLlmResponse = lastStep.observation.code == INVALID_AUTH_HTTP_CODE ? lastStep.llmResponse : ();
                iteration -= 1;
            }
        }
        else {
            log:printError("Invalid request payload", payload = payload);
            return http:BAD_REQUEST;
        }

        string|ExecutionResult|error result;
        // validate the command
        if command == "" {
            return handleServerError(error InvalidCommandError("Command cannot be empty."), EXECUTION, {"id": testCaseId});
        }
        boolean isTestAll = command.toLowerAscii().matches(testAllPattern);

        // TODO stop sending tools to the testGptAgent
        // create the TestGPT agent
        ApiChatAgent|error apiChatAgent = new (command, apiSpec, executionHistory, token, iteration, testCaseId);
        if apiChatAgent is error {
            return handleServerError(apiChatAgent, EXECUTION, {"id": testCaseId});
        }
        // execute the next step using the agent
        if isTestAll {
            result = apiChatAgent.execute(restoredLlmResponse, true);
        } else {
            result = apiChatAgent.execute(restoredLlmResponse);
        }

        if result is error {
            return handleServerError(result, EXECUTION, {"id": testCaseId});
        }
        // check for the completion of the test
        if result is string {
            if iteration > 1 { // cleaning the cache
                _ = start clearTestCaseCache(testCaseId);
            }
            return {
                result
            };
        }

        int statusCode = result.output.code;
        // check for exceeded max iterations
        if iteration >= MAX_ITERATIONS && statusCode != INVALID_AUTH_HTTP_CODE {
            log:printDebug("Max iterations reached. Terminating the task.", id = testCaseId);
            _ = start clearTestCaseCache(testCaseId);
            return {
                taskStatus: TERMINATED,
                result
            };
        }

        // cache the progress
        agent:ExecutionStep lastStep = apiChatAgent.agentExecutor.progress.history.pop();
        executionHistory = [...executionHistory, {llmResponse: lastStep.llmResponse, observation: result.output}];
        _ = start updateTestCaseCache(testCaseId, {
            iteration,
            command,
            apiSpec: apiSpec.cloneReadOnly(),
            executionHistory: executionHistory.cloneReadOnly()
        });

        // check for token expiration, needs to request a new token from frontend
        if statusCode == INVALID_AUTH_HTTP_CODE {
            log:printDebug("Token expired, requesting a new token", id = testCaseId, observation = result.output);
            return {
                taskStatus: EXPIRED_TOKEN
            };
        }
        return {
            taskStatus: IN_PROGRESS,
            result
        };
    }

    # Execute a single API test case while caching the progress. This resource is used by on-prem APIM.
    #
    # + payload - Test initialization request or test execution request
    # + return - Test result
    isolated resource function post chat(@http:Header string x\-request\-id, TestInitializationRequest|TestExecutionResultRequest payload) returns TestExecutionOnPremResponse|TestCompletionResponse|InternalServerError|ErrorInfo|http:BadRequest {
        string testCaseId = x\-request\-id;
        string command;
        int iteration = 1;
        agent:HttpApiSpecification apiSpec;
        TestExecutionStep[] executionHistory = [];

        // check for initial request extract required details to initialize the agent
        if payload is TestInitializationRequest {
            log:printDebug("Agent Initialization Started.", id = testCaseId);
            command = payload.command.trim();
            apiSpec = payload.apiSpec;
        }
        else if payload is TestExecutionResultRequest { // extract details required to restore the agent if it is a progress request
            log:printDebug("Agent Restoration Started.", id = testCaseId);
            CacheRecord|error cachedRecord = retrieveCachedTestCase(testCaseId);
            if cachedRecord is error {
                return handleServerError(error CachingError("Error while retrieving the cached record."), EXECUTION, {"id": testCaseId});
            }
            apiSpec = cachedRecord.apiSpec;
            command = cachedRecord.command;
            iteration = cachedRecord.iteration + 1;
            executionHistory = cachedRecord.executionHistory;
            json cachedLlmResponse = cachedRecord?.previousLlmResponse;
            // update last thought
            executionHistory.push({
                llmResponse: cachedLlmResponse,
                observation: payload.response
            });

        }
        else {
            log:printError("Invalid request payload", payload = payload);
            return http:BAD_REQUEST;
        }

        NextAction|string|error nextAction;
        // validate the command
        if command == "" {
            return handleServerError(error InvalidCommandError("Command cannot be empty."), EXECUTION, {"id": testCaseId});
        }
        boolean isTestAll = command.toLowerAscii().matches(testAllPattern);

        // TODO stop sending tools to the testGptAgent
        // create the TestGPT agent
        ApiChatAgent|error apiChatAgent = new (command, apiSpec, executionHistory, "", iteration, testCaseId);
        if apiChatAgent is error {
            return handleServerError(apiChatAgent, EXECUTION, {"id": testCaseId});
        }
        // execute the next step using the agent
        if isTestAll {
            nextAction = apiChatAgent.chat(true);
        } else {
            nextAction = apiChatAgent.chat();
        }

        if nextAction is error {
            return handleServerError(nextAction, EXECUTION, {"id": testCaseId});
        }
        // check for the completion of the test
        if nextAction is string {
            if iteration > 1 { // cleaning the cache
                _ = start clearTestCaseCache(testCaseId);
            }
            return {
                result: nextAction
            };
        }

        // int statusCode = result.output.code;
        // check for exceeded max iterations
        if iteration >= MAX_ITERATIONS {
            log:printDebug("Max iterations reached. Terminating the task.", id = testCaseId);
            _ = start clearTestCaseCache(testCaseId);
            return {
                taskStatus: TERMINATED,
                'resource: nextAction.'resource
            };
        }

        // cache the progress
        _ = start updateTestCaseCache(testCaseId, {
            iteration,
            command,
            apiSpec: apiSpec.cloneReadOnly(),
            executionHistory: executionHistory.cloneReadOnly(),
            previousLlmResponse: nextAction.llmResponse.cloneReadOnly()
        });

        return {
            taskStatus: IN_PROGRESS,
            'resource: nextAction.'resource
        };
    }

    # Heath check endpoint
    #
    # + return - Health status of the service
    isolated resource function get health() returns http:Ok|http:InternalServerError {
        string|error ping = redis->ping();
        if ping is error {
            log:printWarn("Liveness probe failed.", ping);
            return http:INTERNAL_SERVER_ERROR;
        }
        return http:OK;
    }
}

isolated function readKey(string key) returns string {
    if key.includes("/") {
        string|io:Error keyFromFile = io:fileReadString(key);
        if keyFromFile is io:Error {
            log:printError("Error while reading the key from file.", keyFromFile);
            panic keyFromFile;
        }
        return keyFromFile;
    }
    return key;
}
