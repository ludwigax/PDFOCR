import tiktoken

def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0125"):
    """Return the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model in {
        "gpt-3.5-turbo-0125",
        "gpt-3.5-turbo-1106",
        "gpt-4-0125-preview",
        "gpt-4-1106-preview",
        "gpt-4-0613",
        "gpt-4-32k-0613",
        }:
        tokens_per_message = 3
        tokens_per_name = 1
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif "gpt-3.5-turbo" in model:
        print("Warning: gpt-3.5-turbo may update over time. Returning num tokens assuming gpt-3.5-turbo-0125.")
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0125")
    elif "gpt-4" in model:
        print("Warning: gpt-4 may update over time. Returning num tokens assuming gpt-4-0613.")
        return num_tokens_from_messages(messages, model="gpt-4-0613")
    else:
        raise NotImplementedError(
            f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
        )
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens

price_dict = {
    "gpt-3.5-turbo-0613": 0.5,
    "gpt-4": 30,
    "gpt-4-32k": 60,
    "gpt-4-0125-preview": 10
}



if __name__=="__main__":
    with open("./results/test.txt", "r", encoding="utf-8") as f:
        text = f.read()
    import os
    folder_path = "./results"
    for i, filename in enumerate(os.listdir(folder_path)):
        file_path = os.path.join(folder_path, filename)
        if filename.split(".")[-1]=="txt":
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
                # print(text)
                messages = [
                    {
                        "role": "user",
                        "content": text
                    }
                ]
                tk = num_tokens_from_messages(messages, model="gpt-4-0613")
                print(tk)
                print("single message price", price_dict["gpt-4"] * tk / 1000000)
                print("")



    # print(text)
    # tk = num_tokens_from_messages(messages, model="gpt-4")
    # print(tk)
    # print("single message price", price_dict["gpt-4"] * tk / 1000000)

