# pip install llama-cpp-python
from llama_cpp import Llama

import random
from labeler.generic_labeler import GenericLabeler

MODEL_PATH = "/Users/miro/Downloads/llama.cpp/models/13B/ggml-alpaca-13b-q4.bin"


class LLamaLabeler(GenericLabeler):

  def __init__(self, label, topic, grp1_keywords, grp2_keywords, grp1_page_id, grp2_page_id):
    super().__init__(label, topic, grp1_keywords, grp2_keywords, grp1_page_id, grp2_page_id)
    self.llm = Llama(model_path=MODEL_PATH)

  def lbl(self, graph, article_title, article_extract):
    article_extract = article_extract.strip()
    article_title = article_title.replace("_", " ")
    arguments_answers = []
    for i in range(2):
      prompt = f"Q: Is this extract \"{article_extract}\" in favor of {self.arguments_to_test[i]}?" + \
          " Reply only with YES or NO. A:"
      print(prompt)
      tokens = self.llm.tokenize(prompt.encode("utf-8"))
      for token in self.llm.generate(tokens, top_k=40, top_p=0.95, temp=1.0, repeat_penalty=1.1):
        arguments_answers.append(self.llm.detokenize([token]).decode("utf-8").lower())
    return arguments_answers


if __name__ == "__main__":
  llm = Llama(model_path=MODEL_PATH)
  print("Welcome to the chat! Type 'quit' to exit.")
  while True:
    text = input("Text> ")
    topic = input("Topic> ")
    topic_sides = topic.split(" vs ")
    prompt = f"Q: Is \"{text}\" \n in favor of {topic_sides[0]}? Reply only with YES or NO. A:"
    print(topic_sides[0], ":", end=" ")
    tokens = llm.tokenize(prompt.encode("utf-8"))
    for token in llm.generate(tokens, top_k=40, top_p=0.95, temp=1.0, repeat_penalty=1.1):
      print(llm.detokenize([token]).decode("utf-8").lower())
      break
    prompt = f"Q: Is \"{text}\" \n this in favor of {topic_sides[1]}? Reply only with YES or NO. A:"
    tokens = llm.tokenize(prompt.encode("utf-8"))
    print(topic_sides[1], ":", end=" ")
    for token in llm.generate(tokens, top_k=40, top_p=0.95, temp=1.0, repeat_penalty=1.1):
      print(llm.detokenize([token]).decode("utf-8").lower())
      break
