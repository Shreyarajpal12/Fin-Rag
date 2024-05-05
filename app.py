import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader
import langchain
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings, HuggingFaceInstructEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts.base import BasePromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain import PromptTemplate, LLMChain

from langchain.memory import ConversationBufferMemory
from htmlTemplates import css, bot_template, user_template

# class FinancialAnalystPrompt(BasePromptTemplate):
#     def format_prompt(self, inputs):
#         return f"As a financial analyst, what can you tell about: "

def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def get_text_chunks(text):
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=2000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks

def get_vectorstore(text_chunks):
    embeddings = OpenAIEmbeddings()
    # embeddings = HuggingFaceInstructEmbeddings(model_name="hkunlp/instructor-xl")
    vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
    return vectorstore


def get_conversation_chain(vectorstore):
    llm = ChatOpenAI()
    memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
    # prompt=f"As a financial analyst, what can you tell about"
    
    template = """
Imagine you're assisting in financial analysis for a company like Google.
 Your task is to EXTRACT INFORMATION LIKE TOTAL ASSETS , NET INCOME, TOTAL EXPENSES ETC. FROM  SEC filings for a specific year and
   calculate profitability ratios based on the provided data. Ensure that you:

Analyze the data from balance sheets, income statements, etc., for the specified year.
Extract relevant financial metrics such as revenue, COGS, net income, total expenses, etc.
Calculate the following profitability ratios:
Return on Assets (ROA): Net Income / Total Assets
Gross Profit Margin: (Total Revenue - COGS) / Total Revenue
Operating Profit Margin: Operating Income / Total Revenue
Net Profit Margin: Net Income / Total Revenue
Margin per User: (Total Revenue - Total Expenses) / Number of Users
Compare the calculated ratios for different years to determine better profitability.
Ensure calculations are based solely on the data provided in the SEC filings for the specified year.
Provide the year for analysis, and I'll extract the relevant data and calculate the ratios accordingly.
Question: {question}

Answer:"""


    prompt = PromptTemplate(template=template, input_variables=["question"])
    # print(question)
    llm_chain = LLMChain(prompt=prompt, llm=llm)
    # question_generator_chain = LLMChain(llm=llm, prompt=prompt)
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        condense_question_prompt=prompt,
        memory=memory
    )
    return conversation_chain

def handle_userinput(user_question):
    response = st.session_state.conversation({'question': user_question})
    print(response)
    st.session_state.chat_history = response['chat_history']
    for i, message in enumerate(st.session_state.chat_history):
        if i % 2 == 0:
            st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
        else:
            st.write(bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)

def main():
    load_dotenv()
    st.set_page_config(page_title="Chat with multiple SEC FILINGS", page_icon=":books:")
    st.write(css, unsafe_allow_html=True)
    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None
    st.header("Chat with multiple SEC FILINGS :books:")
    user_question = st.text_input("Ask a question about your documents:")
    if user_question:
        handle_userinput(user_question)
    with st.sidebar:
        st.subheader("Your documents")
        pdf_docs = st.file_uploader("Upload the SEC FILING PDF here and click on 'Process'", accept_multiple_files=True)
        if st.button("Process"):
            with st.spinner("Processing"):
                raw_text = get_pdf_text(pdf_docs)
                text_chunks = get_text_chunks(raw_text)
                vectorstore = get_vectorstore(text_chunks)
                st.session_state.conversation = get_conversation_chain(vectorstore)

if __name__ == '__main__':
    main()
