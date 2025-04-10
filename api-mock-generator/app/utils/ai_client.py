from config.settings import client, deployment_name
import json


def generate_text(prompt):
    # Uncomment and implement properly if needed
    # response = openai.Completion.create(
    #     engine="text-davinci-003",
    #     prompt=prompt,
    #     max_tokens=1000
    # )
    # return response.choices[0].text.strip()
    return "mock script"

def generate_structured_output(sys_msg, user_msg, schema):
    try:
        # Prepare the messages for the API call
        messages = [{"role": "user", "content": user_msg}]
        if sys_msg:
            messages.append({"role": "system", "content": sys_msg})
        messages.append({"role": "user", "content": f"Use the following schema for the output: '{schema}'"})

        # Call the OpenAI API
        response = client.chat.completions.create(
            model=deployment_name,
            response_format={"type": "json_object"},
            messages=messages,
            temperature=0.7
        )

        print(response)

        # Extract and return the content from the response
        return response.choices[0].message.content

    except KeyError as e:
        print(f"KeyError: Missing expected key in the response - {e}")
        return json.dumps({"error": f"KeyError: {e}"})

    except client.exceptions.OpenAIError as e:
        print(f"OpenAI API Error: {e}")
        return json.dumps({"error": f"OpenAI API Error: {e}"})

    except Exception as e:
        print(f"Unexpected error: {e}")
        return json.dumps({"error": f"Unexpected error: {e}"})