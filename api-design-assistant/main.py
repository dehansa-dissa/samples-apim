from methods import query_llm

if __name__ == "__main__":
    while True:
        user_input = input("Enter your API use case or type a synonym of 'modify' to include modifications to the code: ")
        query_llm(user_input)
