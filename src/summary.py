from langchain import OpenAI, PromptTemplate, LLMChain
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains.mapreduce import MapReduceChain
from langchain.prompts import PromptTemplate

import os
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

def summarize(input: str):
    llm = OpenAI(temperature=0, openai_api_key=OPENAI_API_KEY)

    text_splitter = CharacterTextSplitter()