import streamlit as st
import os
from ultis import *
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.sql_database import SQLDatabase
from typing import TypedDict, Annotated, List
import copy
query_prompt_template = hub.pull("langchain-ai/sql-query-system-prompt")
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
assert len(query_prompt_template.messages) == 1
import time 
import copy
import json
import warnings
from langchain_core.prompts import PromptTemplate
warnings.filterwarnings("ignore")

db = SQLDatabase.from_uri(SUPABASE_URI)

execute_query_tool = QuerySQLDatabaseTool(db=db)
print("kết nối db thành công")
# Cấu hình LLM
from langchain.chat_models import init_chat_model
claude = init_chat_model("claude-3-5-sonnet-20241022")
openai = init_chat_model("gpt-4")

# Tạo bộ nhớ hội thoại
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, k = 5)

# Hàm truy vấn dữ liệu từ Supabase
from langchain.schema import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from ultis import FULL_DES_JSON, TERM_DES_JSON, DB_SCHEMA_DESCRIPTION   

def clarify_question(query, chat_history, llm_model):

    def remove_curly_braces(text):
        return text.replace("{", "").replace("}", "")
    
    context = "\n".join([f"Câu hỏi User: {chat['user']} ==> Bot hiểu yêu cầu như sau: {remove_curly_braces(chat['bot'])}" \
                         for chat in chat_history])
    print("========== LỊCH SỬ CONTEXT: ========= \n", context)
    system = DB_SCHEMA_DESCRIPTION \
    + """You are a DB assistant. Dựa trên hội thoại trước: """ + context \
    + """Với câu hỏi hiện tại của User: {question}. """ \
    + """ Nhiệm vụ của bạn là:
    - Hãy diễn giải rõ ràng, chính xác yêu cầu của người dùng hiện tại (HÃY NHỚ RẰNG: những gì bạn không chắc chắn, đừng cho vào, đừng diễn giải, Không ghi cụ thể tên trường dữ liệu, không tóm tắt)
    - Các bảng dữ liệu cần dùng (bắt buộc phải có GSTD_Model Development). Nếu có đề cập tới phân loại theo loại 1, loại 2 hay loại 3 thì phải thêm bảng GSTD_Model Validation vào.  Nếu đề cập phân loại theo Cao, Thấp, Trung bình thì thêm bảng GSTD_Model Risk Rating vào.
    Kết quả cần trả ra là json có key là clarified_question và tables."""

    human = "{question}"
    prompt = ChatPromptTemplate.from_messages([
                                                                                ("system", system), ("human", human)
                                                                            ])

    chain = prompt | llm_model
    tmp = chain.invoke(
        {
            "question": query
        })  

    return tmp.content

# Giao diện Streamlit
st.title("Model-Inventory AI Chatbot")
st.write("Nhập câu hỏi về dữ liệu trong Supabase Database:")

# Lưu hội thoại trong session
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Nhập câu hỏi từ người dùng
user_input = st.text_input("Câu hỏi của bạn?")

if st.button("Send"):
    if user_input:
        start_time = time.time()
        # Lưu câu hỏi vào bộ nhớ
        memory.save_context({"input": user_input}, {"output": ""})

        ################ I. Thực thi query SQL từ AI với ngữ cảnh hội thoại ################
        result_1 = clarify_question(user_input, st.session_state.chat_history, claude)
        print("****** Result_1: ", result_1)
        st.write("****** Câu hỏi được làm rõ ******: ", result_1)

        # tách thông tin từ kết quả trả về
        result_1 = json.loads(result_1)
        clarified_question = result_1["clarified_question"]
        tables_to_extract = result_1["tables"]

        ################ II. Extract thông tin cần thiết ################
        
        def extract_tables_from_json(json_data, tables_to_extract):
            """
            Hàm trích xuất thông tin từ JSON dựa trên danh sách các bảng cho trước.
            
            Args:
                json_data (str or dict): Dữ liệu JSON dưới dạng chuỗi hoặc dictionary.
                tables_to_extract (list): Danh sách các bảng cần trích xuất.
            Returns:
                dict: Dictionary chứa dữ liệu của các bảng được yêu cầu.
            """
            # Nếu đầu vào là chuỗi JSON, chuyển đổi thành dictionary
            if isinstance(json_data, str):
                json_data = json.loads(json_data)
            # Lọc các bảng theo danh sách yêu cầu
            extracted_data = {table: json_data[table] for table in tables_to_extract if table in json_data}
            return extracted_data

        info_dict = {
            "question": clarified_question,
            "input": extract_tables_from_json(FULL_DES_JSON, tables_to_extract)    
        }

        ################# III: xây dựng câu lệnh query ################
        from langchain_community.agent_toolkits import SQLDatabaseToolkit
        from typing_extensions import Annotated
        toolkit = SQLDatabaseToolkit(db=db, llm=claude)
        tools = toolkit.get_tools()

        from langgraph.prebuilt import create_react_agent

        def write_query(llm_model, info_dict):

            prompt = PromptTemplate.from_template(
                (TERM_DES_JSON + """
                    Bạn nhận được thông tin các bảng dữ liệu, các trường dữ liệu liên quan là {input}. 
                    Bạn hãy xây dựng câu lệnh query {dialect} cho phù hợp với yêu cầu người dùng. 
                    You have access to the following tools:{tools}

                    Lưu ý:
                    - TÊN CÁC BẢNG, CỘT PHẢI ĐỂ TRONG ""
                    - Việc mapping các bảng dựa trên trường DevelopmentID. Trường DevelopmenID không phải là ModelID. Không được dùng DevelopmenID = ModelID
                    - Câu lệnh phải tuân thủ nguyên tắc của {dialect} trong Supabase.
                    - Các TRƯỜNG DATE (tên trường có chữ date) phải được chuyển đổi về int với giá trị không null, rồi mới sử dụng. Lưu ý: các trường này có thể tồn tại giá trị NULL hoặc missing.
                    - Bạn phải rà soát câu hỏi người dùng để đảm bảo câu lệnh trả về kết quả chính xác.
                    - Đừng tự thêm điều kiện where mà người dùng không cần
                    - Không thêm ký tự \n, \ không cần thiết.

                    Bạn chỉ được trả ra câu lệnh query (không thêm bất kỳ thông tin nào khác) mà phải chạy được. Only return the Query, no explanation, no description.

                    Use the following format:
                    Question: the input question you must answer
                    Thought: you should always think about what to do
                    Action: the action to take, should be one of {tools}
                    Action Input: the input to the action
                    Observation: the result of the action
                    ... (this Thought/Action/Action Input/Observation can repeat N times)
                    Thought: I now know the final answer
                    Final Answer: the final answer to the original input question

                    Begin!
                    Question: {question}
                """)
            )

            # Format prompt với dữ liệu thực tế
            formatted_prompt = prompt.format(
                dialect="PostgreSQL",
                question=info_dict["question"],
                input=info_dict["input"],
                tools= """["QuerySQLDatabaseTool", "InfoSQLDatabaseTool", "ListSQLDatabaseTool", "QuerySQLCheckerTool"]"""
            )

            # 🛠 Tạo Agent Executor (Dùng Prompt ĐÃ FORMAT)
            agent_executor = create_react_agent(llm_model, tools, prompt=formatted_prompt)
            answer = agent_executor.invoke({"messages": [{"role": "user", "content": info_dict["question"]}]})

            def extract_sql_from_final_answer(text):
                """Trích xuất câu SQL từ nội dung chứa 'Final Answer:'"""
                keyword = "Final Answer:"
                if keyword in text:
                    return text.split(keyword, 1)[1].strip()
                return text

            return {"query": extract_sql_from_final_answer(answer["messages"][1].content)}
        
        result_3 = write_query(claude, info_dict)
        print("******Câu lệnh là :******", result_3["query"])
        st.write("******Câu lệnh là: ******", result_3["query"])

        # IV. Thực thi câu lệnh query
        
        def execute_query(state):
            """Execute SQL query."""
            
            return {"result": execute_query_tool.invoke(state["query"])}

        result_4 = execute_query(result_3)
        st.write("Kết quả thực thi câu lệnh : ", result_4["result"])

        # V. Trả lời
        def generate_answer(state, model):
            """Answer question using retrieved information as context."""
            prompt = (
                """
                Given the following user question, corresponding query, 
                and db retrieval result, answer the user question.\n\n
                Question: {}

                SQL Result: {}
                
                Trình bày đẹp, bỏ các ký tự \n đi
                """.format(state["question"], state["result"])
            )
            response = model.invoke(prompt)
            return response.content
        
        result_5 = generate_answer({"question":clarified_question, "result": result_4 }, openai)
        st.write("******Kết quả trả lời : ******", result_5)

    # VI. Hiển thị:
    def remove_newlines(text):
        return text.replace("\n", "")

    response_text = "1. Câu hỏi làm rõ: " + clarified_question +  "----" +  "\n 2. Câu lệnh query: " + result_3["query"] +  "----" +  "\n 3. Kết quả:  " + str(result_5)
    # response_text = remove_newlines(response_text)
    st.write(response_text, "\n 4. Thời gian thực thi: ", time.time() - start_time)
    
    def summarize_query(db_query, model):
        """mô tả các điều kiện where trong câu lệnh"""
        prompt = (
            """
            Dựa vào câu query, hãy mô tả ngắn gọn nhưng vẫn đủ các ý phạm vi lấy dữ liệu (các điều kiện where)
            Query: {}            

            """.format(db_query)
        )
        response = model.invoke(prompt)
        return response.content
 
    summarized_where_query = summarize_query(result_3["query"], openai)
    st.session_state.chat_history.append({"user": user_input, \
                                                                "bot": clarified_question + ". Từ đó, Cách Bot thực hiện là : " + str(summarized_where_query)})

# Hiển thị lịch sử hội thoại
st.subheader(" Lịch sử hội thoại ")
for chat in st.session_state.chat_history:
    st.write(f"**Bạn:** {chat['user']}")
    st.write(f"**Bot:** {chat['bot']}")
