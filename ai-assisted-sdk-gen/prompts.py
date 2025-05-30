"""
 Copyright (c) 2025, WSO2 LLC. (http://www.wso2.com). All Rights Reserved.

  This software is the property of WSO2 LLC. and its suppliers, if any.
  Dissemination of any information or reproduction of any material contained
  herein is strictly forbidden, unless permitted by WSO2 in accordance with
  the WSO2 Commercial License available at http://wso2.com/licenses.
  For specific language governing the permissions and limitations under
  this license, please see the license as well as any agreement you’ve
  entered into with WSO2 governing the purchase of this software and any
"""
from langchain.prompts import PromptTemplate

merge_specs_prompt = """

Api Specifications :
{specs_text}

Api Names and their respective contexts:
{api_contexts}

PRIMARY OBJECTIVES: 
1. Merge the provided API specifications into a single cohesive specification.
2. Prefix all resource paths with their corresponding API context and version.
3. Create an appropriate title and description for the merged API.
4. The server URL of the merged API should always be given as :
    servers:
    - url: https://localhost:8243
    - url: http://localhost:8280

CRITICAL REQUIREMENTS:
- EVERY endpoint path MUST be prefixed with its corresponding API context and version.
- Preserve the EXACT case sensitivity of all identifiers (paths, parameters, schemas, etc.).
- Maintain all security definitions, schemas, and other components.
- Resolve any conflicts between duplicate operations or schemas.
- Ensure the output is valid OpenAPI/Swagger specification.

STRICT CONSTRAINTS:
- DO NOT modify the original API contexts or versions in any way.
- DO NOT use generic titles like "Merged API" - create a meaningful title that reflects the combined functionality.
- DO NOT include any markdown code block formatting or language indicators in your response.
- DO NOT include any explanations or comments outside the specification.
- DO NOT include any text before or after the specification.

OUTPUT FORMAT
Provide ONLY the complete merged OpenAPI specification as valid JSON without any surrounding text, explanations, or markdown formatting.
"""

def create_merge_specs_prompt(specs_text, api_contexts):
    return PromptTemplate(
        input_variables=["specs_text", "api_contexts"],
        template=merge_specs_prompt
    )

summarize_spec_prompt = """
You are an expert and an Intelligent API documentation specialist.

Your task is to extract ONLY the parts of the API specification that are required for the user's goal — WITHOUT losing any field names, schema references, or structural integrity. 
You MUST ensure that the ENTIRE use case can be fulfilled.

USER'S GOAL: {use_case}

FULL API SPECIFICATION:
    <mergedSpec>
        {merged_spec}
    </mergedSpec>

Please follow these instructions strictly:

1. Include ALL the relevant endpoints, HTTP methods, request/response formats, and ALL schemas used.

2. For each endpoint, show:

    a. Method and path (e.g., POST /shipments)

    b. Request body schema:
        - If it uses a `$ref`, include the `$ref` line exactly as it appears (e.g: `_productcatalog_1_0_0_products_get_200_response`).
        - Do NOT inline or resolve the schema reference here.
        - Fields with their types, descriptions, and nested references (if any).

    c. Response body schema:
        - Same rule as above — include the `$ref` line exactly as it appears if used (e.g: `_productcatalog_1_0_0_products_get_200_response`).
        - Fields with their types, descriptions, and nested references (if any).
        - For arrays, specify the item type and include the schema it references.

3. You MUST EXPLICITLY LIST the FULL and unmodified schema definitions for BOTH request body schemas and response body schemas for each `$ref` used in any endpoint above:
    - Use the EXACT name of the schema (e.g: `_productcatalog_1_0_0_products_get_200_response`).
    - Include the COMPLETE schema body as defined under `components/schemas`.
    - If the schema contains nested `$ref`, include those nested definitions as well (under the same `Included Schema Definitions` section), but still maintain them by name — do NOT inline or merge.
    - You MUST INCLUDE ALL request body schemas and response body schemas for each `$ref` used in any endpoint.
    - Ensure that every schema is fully detailed. No omissions or vague descriptions are allowed.
    - DO NOT give vague definitions such as "Product creation details" or "Updated product information" without giving the full schema.
    - DO NOT limit schema details based on length or space concerns. Completeness is the priority.

4. Maintain all original field names, schema names, object names, and structure. DO NOT rename, paraphrase, or shorten anything.

5. Highlight any warnings or required fields explicitly marked in the specification.

DO NOT:
- Rename fields (e.g., `address_from` must NOT become `fromAddress`).
- Generalize or paraphrase structures or types.
- Include unrelated endpoints.
- Add examples or natural language summaries,

NAMING INSTRUCTIONS:
- Always use the exact names of components from the `components/schemas` section. 
- DO NOT generalize schemas (Example: avoid saying "array of product objects" — instead say `List<ProductCatalogAPI100ProductsGet200ResponseProductsInner>`).

You MUST ALWAYS Respond with ONLY the extracted API specification AND ALL the FULL Schema Definitions in a clean, structured, human-readable format (not JSON or YAML) WITHOUT FAIL.

"""

def create_summarization_prompt():
    return PromptTemplate(
        input_variables=["use_case", "merged_spec"],
        template=summarize_spec_prompt
    )

method_mapping_prompt = """
You are an expert in identifying the matching SDK methods included in the summarized specification.

Given below is the summarized API specification.
<summarizedSpec>
    {summarized_spec}
</summarizedSpec>

Your task is to identify and list ALL the associated SDK method(s) AND extracted documentation comments that implement or call that endpoint. 
Given below is the SDK methods and documentation comments from which you will have to identify and list from.

SDK METHODS & DOCUMENTATION COMMENTS:
    <sdkMethods>
        {formatted_methods}
    </sdkMethods>

For each endpoint given in the summarized soecification: 
- Identify and list ALL the matching SDK method(s) from the list given in SDK Methods.
- Return:
  - The **method name** (EXACTLY as provided)
  - The @param, @return, @throws mentioned in the documentation comments.
- Match strictly based on endpoint path and HTTP method.
- Do NOT alter or paraphrase any method name or documentation comments.

"""

def create_method_mapping_prompt():
    return PromptTemplate(
        input_variables=["summarized_spec", "formatted_methods"],
        template=method_mapping_prompt
    )

code_generation_prompt = """
Role and Objective:
You are a senior software engineer specializing in implementing {language} Application code based on SDK methods. 

Your primary goal is to generate production-ready {language} code that COMPLETELY implements the given use case using the provided SDK methods and data models EXACTLY as defined.
- User's Use Case:
  "{question}"  

You MUST follow these Instructions:

1. Carefully analyse and use the SDK Methods and use the Information provided based on the OpenAPI Specification:
- A summary of the OpenAPI specification along with the associated sdk method names, model class names, and fields is provided to give further insight into the API endpoints, request/response formats, and additional details required for implementation. 

    OPEN API SPEC SUMMARY:
    - <specificationSummary>
        {merged_spec}
      </specificationSummary>

    - SDK METHODS AND JAVADOCS:
      <sdkMethods>
         {sdk_methods}
      </sdkMethods>

   - YOU MUST STRICTLY USE ONLY the method names, model class names, and data fields EXACTLY AS THEY APPEAR in the <specificationSummary>.
   - DO NOT invent or generate any new method names, model class names, request/response fields, or paths.
   - The return types of the methods are provided in the documentation comments. You MUST ENSURE the return types are STRICTLY ADHERED TO when constructing methods.
   - Always match the parameter and return types as described.

2. Refer to the Example:
   - Use the given example client application as a reference for best practices in structuring the logic and handling API calls.
   - Always implement OAuth2 token automation logic before making API calls as shown, including:
        - Implementing the getOAuth2AccessToken() method to retrieve tokens.
        - Applying the obtained access token to the API client authentication.
   - <exampleCode>
        ```{language}
            {example_code}
        ``` 
     </exampleCode>


3. Data Type Guidelines:
   - For numeric values: Use the actual numeric type, not strings.
   - For dates: Use appropriate date objects for manipulation, convert to string only when passing to API.
   - Field names must exactly match those in the model classes. DO NOT invent your own fields.
   - Nested objects within schemas are implemented as separate classes with names that follow the pattern: [ParentClassName][NestedObjectName]
            - Example: For OrderRequest with a nested BillingAddress object, use OrderRequestBillingAddress

4. {language_specific_instructions}

5. Plan your code structure:
   - Determine the appropriate response types based on the method documentation in <specificationSummary> and <sdkMethods>.
   - If the request and response types of the endpoints clash between <specificationSummary> and <sdkMethods>, you MUST ALWAYS STICK TO the request and response types mentioned in the <sdkMethods>.

6. Generate the {language} Application code:
   - Implement a well-structured and functional {language} application code that covers the entire use case utilizing the provided SDK methods. 
   - The implementation MUST follow best practices, including error handling and API response processing. Ensure OOP Principles are followed and sub methods to fulfill each task is used. 
   - Implement the main function to address the use case requirements.
   - You MUST ONLY use the method names, models, and field names that are specified in the SDK method names list and <specificationSummary>.
   - STRICT CONDITION: DO NOT create or hallucinate method names, models, or fields that are not provided.
   - You MUST ONLY return the {language} source code. No additional text, explanations, or annotations are permitted.
   - you MUST ENSURE that all functions, methods, helper methods are provided with COMPLETE IMPLEMENTATION.
   - STRICT CONDITION: DO NOT specify the language ({language}) when providing the answer.

7. Review and refine your code:
   - Check that all use case requirements are met.
   - VERIFY that ONLY the SDK methods and models from the provided <specificationSummary> are used.
   - Ensure the code follows coding best practices and conventions for {language}.
   - Ensure you have STRICTLY followed the guidelines provided.

"""

def create_code_gen_prompt():
    return PromptTemplate(
        input_variables=["question", "merged_spec", "sdk_methods", "language", "example_code", "language_specification_instructions"],
        template=code_generation_prompt
    )

def get_language_specific_content(language):
    if language.lower() == "java":

        example_code = """
        import org.wso2.client.api.ApiClient;
        import org.wso2.client.api.ApiException;
        import org.wso2.client.api.Configuration;
        import org.wso2.client.api.auth.*;
        import org.wso2.client.api.models.*;
        import org.wso2.client.api.PizzaShackAPI.DefaultApi;

        import java.io.BufferedReader;
        import java.io.InputStreamReader;
        import java.io.OutputStream;
        import java.net.HttpURLConnection;
        import java.net.URL;
        import java.nio.charset.StandardCharsets;
        import java.util.Base64;
        import java.util.List;
        import javax.net.ssl.HttpsURLConnection;
        import javax.net.ssl.SSLContext;
        import javax.net.ssl.TrustManager;
        import javax.net.ssl.X509TrustManager;
        import java.security.cert.X509Certificate;
        import org.json.JSONObject;

        public class Example {
            
            private static final String TOKEN_ENDPOINT = "https://localhost:9443/oauth2/token";
            private static final String CONSUMER_KEY = "YOUR_CONSUMER_KEY";
            private static final String CONSUMER_SECRET = "YOUR_CONSUMER_SECRET";
            private static final String USERNAME = "YOUR_USERNAME";
            private static final String PASSWORD = "YOUR_PASSWORD";
            
            public static void main(String[] args) {
                try {
                    String accessToken = getOAuth2AccessToken();
                
                    ApiClient defaultClient = Configuration.getDefaultApiClient();
                    defaultClient.setBasePath("http://localhost:8280");

                    OAuth defaultAuth = (OAuth) defaultClient.getAuthentication("default");
                    defaultAuth.setAccessToken(accessToken);
                    
                    DefaultApi apiInstance = new DefaultApi(defaultClient);
                    try {
                        List<MenuItem> result = apiInstance.menuGet();
                        System.out.println(result);
                    } catch (ApiException e) {
                        System.err.println("Exception when calling DefaultApi#menuGet");
                        System.err.println("Status code: " + e.getCode());
                        System.err.println("Reason: " + e.getResponseBody());
                        System.err.println("Response headers: " + e.getResponseHeaders());
                        e.printStackTrace();
                    }
                } catch (Exception e) {
                    System.err.println("Error obtaining OAuth token");
                    e.printStackTrace();
                }
            }

            private static String getOAuth2AccessToken() throws Exception {
                disableSSLVerification();

                URL url = new URL(TOKEN_ENDPOINT);
                HttpURLConnection connection = (HttpURLConnection) url.openConnection();

                connection.setRequestMethod("POST");
                String auth = CONSUMER_KEY + ":" + CONSUMER_SECRET;
                String encodedAuth = Base64.getEncoder().encodeToString(auth.getBytes(StandardCharsets.UTF_8));
                connection.setRequestProperty("Authorization", "Basic " + encodedAuth);
                connection.setRequestProperty("Content-Type", "application/x-www-form-urlencoded");
                connection.setDoOutput(true);
                String requestBody = "grant_type=password&username=" + USERNAME + "&password=" + PASSWORD;
                try (OutputStream os = connection.getOutputStream()) {
                    byte[] input = requestBody.getBytes(StandardCharsets.UTF_8);
                    os.write(input, 0, input.length);
                }

                int responseCode = connection.getResponseCode();
                StringBuilder response = new StringBuilder();
                try (BufferedReader br = new BufferedReader(
                        new InputStreamReader(connection.getInputStream(), StandardCharsets.UTF_8))) {
                    String responseLine;
                    while ((responseLine = br.readLine()) != null) {
                        response.append(responseLine.trim());
                    }
                }

                connection.disconnect();

                JSONObject jsonResponse = new JSONObject(response.toString());
                return jsonResponse.getString("access_token");
            }

            private static void disableSSLVerification() {
                try {
                    TrustManager[] trustAllCerts = new TrustManager[]{
                        new X509TrustManager() {
                            public X509Certificate[] getAcceptedIssuers() {
                                return null;
                            }
                            
                            public void checkClientTrusted(X509Certificate[] certs, String authType) {
                            }
                            
                            public void checkServerTrusted(X509Certificate[] certs, String authType) {
                            }
                        }
                    };
                    
                    SSLContext sc = SSLContext.getInstance("SSL");
                    sc.init(null, trustAllCerts, new java.security.SecureRandom());
                    HttpsURLConnection.setDefaultSSLSocketFactory(sc.getSocketFactory());

                    HttpsURLConnection.setDefaultHostnameVerifier((hostname, session) -> true);
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        }

        """

        language_specific_instructions = """
        - For all fields: Use method chaining (.fieldName(value)) rather than setter methods.
        - You MUST always create an instance of DefaultAPI and pass the Default client to access the methods in the SDK as provided in the example. 
        - DO NOT create your own Default client.
        - Use the imports provided as this is where access is given to the SDK methods:
            - For any usecase provided, you MUST ALWAYS include these imports in the code
            - STRICT CONDITION: DO NOT Modify the imports in any way.
            - <imports>
                    import org.wso2.client.api.ApiClient;
                    import org.wso2.client.api.ApiException;
                    import org.wso2.client.api.Configuration;
                    import org.wso2.client.api.auth.*;
                    import org.wso2.client.model.Merged_SDK.*;
                    import org.wso2.client.api.Merged_SDK.DefaultApi;
                </imports>
        - When planning the code structure, You MUST include the main method which provides the sequence of method calls to fulfill the usecase.

        """
        
    elif language.lower() in ["javascript", "js"]:

        example_code = """
        const CONSUMER_KEY = 'YOUR_CONSUMER_KEY';
        const CONSUMER_SECRET = 'YOUR_CONSUMER_SECRET';
        const USERNAME = 'YOUR_USERNAME';
        const PASSWORD = 'YOUR_PASSWORD';
        const TOKEN_ENDPOINT = 'https://localhost:9443/oauth2/token';

        async function getOAuth2AccessToken() {
        const authString = `${CONSUMER_KEY}:${CONSUMER_SECRET}`;
        const base64Auth = Buffer.from(authString).toString('base64');

        const params = new URLSearchParams();
        params.append('grant_type', 'password');
        params.append('username', USERNAME);
        params.append('password', PASSWORD);

        const https = require('https');
        const querystring = require('querystring');
        
        return new Promise((resolve, reject) => {

            const postData = querystring.stringify({
            grant_type: 'password',
            username: USERNAME,
            password: PASSWORD
            });

            const options = {
            hostname: 'localhost',
            port: 9443,
            path: '/oauth2/token',
            method: 'POST',
            headers: {
                'Authorization': `Basic ${base64Auth}`,
                'Content-Type': 'application/x-www-form-urlencoded',
                'Content-Length': Buffer.byteLength(postData)
            },
            rejectUnauthorized: false
            };

            const req = https.request(options, (res) => {
            let data = '';
            
            res.on('data', (chunk) => {
                data += chunk;
            });
            
            res.on('end', () => {
                if (res.statusCode >= 200 && res.statusCode < 300) {
                try {
                    const tokenData = JSON.parse(data);
                    resolve(tokenData.access_token);
                } catch (e) {
                    reject(new Error(`Failed to parse response: ${e.message}`));
                }
                } else {
                reject(new Error(`HTTP error: ${res.statusCode} ${data}`));
                }
            });
            });
            
            req.on('error', (e) => {
            reject(new Error(`Request failed: ${e.message}`));
            });

            req.write(postData);
            req.end();
        });
        }

        (async function() {
        try {
            const accessToken = await getOAuth2AccessToken();
            
            var PizzaShackApi = require('pizza_shack_api');
            var defaultClient = PizzaShackApi.ApiClient.instance;
            defaultClient.basePath = 'http://localhost:8280';
            var defaultAuth = defaultClient.authentications['default'];
            defaultAuth.accessToken = accessToken;
            var api = new PizzaShackApi.DefaultApi()
            var callback = function(error, data, response) {
            if (error) {
                console.error(error);
            } else {
                console.log('API called successfully. Returned data: ' + data);
            }
            };
            api.menuGet(callback);
        } catch (error) {
            console.error("Error obtaining OAuth token:", error);
        }
        })();

        """

        language_specific_instructions = """
        - You MUST always create an instance of DefaultApi and configure the API client authentication as shown in the example below. Always use the callback pattern shown in the example.
        - For all fields: Set properties directly on objects (object.property = value) following the SDK patterns.
        - When planning the code structure, you MUST include a `main()` function that clearly demonstrates the complete workflow by showing the precise sequence of method calls needed to fulfill the use case. 
        - Structure your code with separate, well-documented functions for distinct responsibilities that are orchestrated by this main function.

        """
   
    return {
        "example_code": example_code,
        "language_specific_instructions": language_specific_instructions
    }