// Copyright (c) 2023, WSO2 LLC. (http://www.wso2.com). All Rights Reserved.
//
// This software is the property of WSO2 Inc. and its suppliers, if any.
// Dissemination of any information or reproduction of any material contained
// herein is strictly forbidden, unless permitted by WSO2 in accordance with
// the WSO2 Commercial License available at http://wso2.com/licenses.
// For specific language governing the permissions and limitations under
// this license, please see the license as well as any agreement you’ve
// entered into with WSO2 governing the purchase of this software and any

const int SERVICE_PORT = 9090;
const int SERVICE_MAX_HEADER_SIZE = 15000;

const int MAX_ITERATIONS = 15;
const int MAX_TOKEN_COUNT = 4096;

const int REDIS_CONN_TIMEOUT = 2000;
const int INVALID_AUTH_HTTP_CODE = 401;

const decimal CACHE_RETRY_INTERVAL = 5;
const decimal AGENT_RETRY_INTERVAL = 1;

const int REDIS_TESTCASE_KEY_EXPIRATION_TIME = 1000;
const int REDIS_OPENAPI_KEY_EXPIRATION_TIME = 5000;

const string TESTCASE_NAMESPACE = "TESTCASE";
const string API_SPEC_NAMESPACE = "API_SPEC";

const string TEST_ALL_RESOURCES_COMMAND = "Invoke all resources";

const string QUERY_PARAM_KEY = "queryParameters";
const string PATH_PARAM_KEY = "pathParameters";
const string REQUEST_BODY_KEY = "requestBody";

const string CHAT_BOT_TOOL_NAME = "ChatBot";

const FINAL_ANSWER_KEY = "final answer";

const int TESTGPT_RETRY_COUNT = 2;
const int CACHE_RETRY_COUNT = 2;
const int CHATBOT_RETRY_COUNT = 1;

const int COMPLETION_MAX_TOKEN_COUNT = 500;
