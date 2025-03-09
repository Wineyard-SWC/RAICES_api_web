#from dotenv import load_dotenv

# Standard library imports
import os
# Third-party imports
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain.chains.retrieval import create_retrieval_chain 
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
# Local application imports

#load_dotenv(dotenv_path='../.env')

KEY = os.getenv("GEMINI_API_KEY")

class ProjectAssistantAI:
    def __init__(self, subdirectory, embedding_model = "models/embedding-001"):
        pdf_directory = os.path.join(os.path.dirname(__file__), 'pdfs', subdirectory)
        self.pdf_paths = [os.path.join(pdf_directory, f) for f in os.listdir(pdf_directory) if f.endswith('.pdf')]
        self.embedding_model = embedding_model
        self.vectorestore=None
        self.llm = ChatGoogleGenerativeAI(
            api_key=KEY,
            model="gemini-1.5-pro",
            temperature=0.2,
            max_tokens=None,
            timeout=None
        )
        self.load_and_vectorize_documents()

    def load_and_vectorize_documents(self):
        documents = []
        for path in self.pdf_paths:
            loader = PyPDFLoader(path)
            data = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000)
            docs = text_splitter.split_documents(data)
            documents.extend(docs)
        self.vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=GoogleGenerativeAIEmbeddings(google_api_key=KEY,model=self.embedding_model)
        )

    async def generate_content(self, query, preprompt):
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", f"{preprompt} Utiliza la información siguiente para profundizar y enriquecer tu respuesta o como una base para construir lo que se te pide:" + "\n\n{context}"),
            ("human", f"Pregunta: {query}")
        ])
        question_answer_chain = create_stuff_documents_chain(self.llm, prompt_template)
        rag_chain = create_retrieval_chain(self.vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5}), question_answer_chain)
        response = rag_chain.invoke({"input": query})
        return response['answer']