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
    messages = [{"role": "user", "content": user_msg}]
    if sys_msg:
        messages.append({"role": "system", "content": sys_msg})
    messages.append({"role": "user", "content": f"Use the following schema for the output: '{schema}'"})

    response = client.chat.completions.create(
        model=deployment_name,
        response_format={"type": "json_object"},
        messages=messages,
        temperature=0.7
    )
    
    return response.choices[0].message.content