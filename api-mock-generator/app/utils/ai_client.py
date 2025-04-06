from config.settings import client, deployment_name


def generate_text(prompt):
    # Uncomment and implement properly if needed
    # response = openai.Completion.create(
    #     engine="text-davinci-003",
    #     prompt=prompt,
    #     max_tokens=1000
    # )
    # return response.choices[0].text.strip()
    return "mock script"

def generate_structured_output(sys_msg,user_msg, schema):
    # Call the OpenAI API
    response = client.chat.completions.create(
        model=deployment_name,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": sys_msg},
            {"role": "user", "content":  user_msg},
            {"role": "user", "content": f"Use the following schema for the output: '{schema}'"}
        ],
        temperature=0.7
    )
    
    return response.choices[0].message.content