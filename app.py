import os
import time
import json
import copy
import warnings
from typing import TypedDict, Annotated, List

import streamlit as st
import copy
from ultis import *
from ultis import SYSTEM_PROMPT_CONTEXT
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from typing_extensions import Annotated
# from langchain.chat_models import ChatOpenAI, init_chat_model
from langchain.memory import ConversationBufferMemory
from langchain.sql_database import SQLDatabase
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain.schema import HumanMessage
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langgraph.prebuilt import create_react_agent
import pandas as pd
from langchain_community.tools.sql_database.tool import QuerySQLCheckerTool

# Load SQL query system prompt
query_prompt_template = hub.pull("langchain-ai/sql-query-system-prompt")
assert len(query_prompt_template.messages) == 1

warnings.filterwarnings("ignore")
from functools import lru_cache


# Cấu hình db
db = SQLDatabase.from_uri(SUPABASE_URI)
execute_query_tool = QuerySQLDatabaseTool(db=db)
print("kết nối db thành công")

# Cấu hình LLM
from langchain_community.chat_models import ChatOpenAI
openai = ChatOpenAI(model_name="gpt-4")
claude = init_chat_model("claude-3-5-sonnet-20241022", temperature=0.5)

# Tạo bộ nhớ hội thoại
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, k = 5)

from langchain_anthropic import ChatAnthropic
anthropic_client = ChatAnthropic(
    model="claude-3-7-sonnet",
    temperature=0,
    extra_headers={"anthropic-beta": "prompt-caching-2025-07-31"}


def clarify_question(query, chat_history, llm_model):

    def remove_curly_braces(text):
        return text.replace("{", "").replace("}", "")
    
    context = ""
    previous_query = None
    previous_bot_response = None
    if chat_history:
        for chat in reversed(chat_history):
            context += f"Câu hỏi User: {chat['user']} ==> Bot trả lời: {remove_curly_braces(chat['bot'])}\n"
            if previous_query is None: 
                previous_query = chat['user']
                previous_bot_response = chat['bot']
    
    # System prompt là phần cố định để cache
    system_role_message = SYSTEM_PROMPT_CONTEXT + \
    """
    Bạn là chuyên viên phòng mô hình, cẩn thận và chính xác. Bạn đã có được thông tin về các bảng dữ liệu, thuật ngữ. 
    Nhiệm vụ của bạn là:
    - Diễn giải rõ ràng, chính xác yêu cầu của người dùng hiện tại dựa trên ngữ cảnh hội thoại trước.
    - Nếu câu hỏi hiện tại yêu cầu "làm rõ hơn" hoặc "sửa lỗi", hãy kết hợp với câu hỏi trước để làm rõ ý định đầy đủ.
    - Nếu câu hỏi trước có câu lệnh SQL sai (trong phản hồi của bot), hãy ghi nhận lỗi đó và đảm bảo yêu cầu mới tránh lỗi tương tự.
    - Không đoán mò hoặc thêm thông tin không chắc chắn. Không ghi cụ thể tên trường dữ liệu, không tóm tắt quá mức.
    - Các bảng dữ liệu cần dùng: bắt buộc có "GSTD_Model Development". Nếu có phân loại theo loại 1, loại 2, loại 3 thì thêm "GSTD_Model Validation". Nếu có phân loại theo Cao, Thấp, Trung bình thì thêm "GSTD_Model Risk Rating".
    
    Kết quả trả ra là JSON với 2 key:
    - "clarified_question": Yêu cầu đã được làm rõ, kết hợp ngữ cảnh nếu cần.
    - "tables": Danh sách các bảng cần dùng.
        """

    # Xác định human input dựa trên điều kiện
    if "làm rõ hơn" in query.lower() and previous_query:
        human = f"Yêu cầu làm rõ hơn thông tin từ câu hỏi trước: '{previous_query}'. Câu hỏi hiện tại: {query}"
    elif "sai rồi" in query.lower() and previous_bot_response and "SELECT" in previous_bot_response:
        human = f"Yêu cầu sửa lỗi từ câu hỏi trước: '{previous_query}' với câu lệnh SQL trước đó: '{previous_bot_response}'. Câu hỏi hiện tại: {query}"
    else:
        human = query
    
    # Tạo messages với Prompt Caching
    messages = {
                        "role": "user",
                        "content": [
                                            {
                                                "type": "text",
                                                "text": system_role_message,
                                                "cache_control": {"type": "ephemeral"}  # Cache system prompt
                                            },
                                            {
                                                "type": "text",
                                                "text": context
                                            },
                                            {   
                                                "type": "text",
                                                "text": human
                                            },
                                        ]
                    }

    # Gọi API Anthropic với Prompt Caching
    response = llm_model.messages.create(
        messages=messages,
        stream=False
    )

    result = response.content[0].text
    return result

# Giao diện Streamlit
st.title("Model-Inventory AI Chatbot")

# Lưu hội thoại trong session
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Nhập câu hỏi từ người dùng
user_input = st.text_input("Tôi có thể giúp gì cho bạn :")

if st.button("Send"):
    if user_input:
        print("===============BẮT ĐẦU===============")
        start_time = time.time()
        # Lưu câu hỏi vào bộ nhớ
        memory.save_context({"input": user_input}, {"output": ""})

        ################ I. Thực thi query SQL từ AI với ngữ cảnh hội thoại ################
        result_1 = clarify_question(user_input, st.session_state.chat_history, anthropic_client)
    
        print("-------------------------Kết quả bước 1: -------------------------\n", result_1)

        # tách thông tin từ kết quả trả về
        if isinstance(result_1, dict):
            print("result_1 đã là dictionary, không cần json.loads()")
        else:
            import re
            match = re.search(r'\{.*\}', result_1, re.DOTALL)
            result_1 = match.group(0)
            result_1 = result_1.replace("\n", "  ")
            result_1 = json.loads(result_1)

        clarified_question = result_1["clarified_question"]
        st.write("**câu hỏi được làm rõ**: ", clarified_question)
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
        
        toolkit = SQLDatabaseToolkit(db=db, llm=claude)
        tools = toolkit.get_tools()

        from langgraph.prebuilt import create_react_agent
        info_dict["error"] = None

        from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
        anthropic_client = Anthropic(api_key="your-anthropic-api-key")

        def write_query(llm_model=anthropic_client, info_dict=None, error=None):
            # System prompt là phần cố định để cache (bao gồm TERM_DES_JSON và hướng dẫn)
            system_prompt = TERM_DES_JSON + """
                            Bạn là chuyên viên phòng mô hình.
                            Bạn là người cẩn thận, chính xác.       
                            Bạn nhận được thông tin các bảng dữ liệu, các trường dữ liệu liên quan là {input}. 
                            Bạn hãy xây dựng câu lệnh query {dialect} cho phù hợp với yêu cầu người dùng. 
                            You have access to the following tools:{tools}

                            Bạn có danh sách các từ sau về thuật ngữ và các trường dữ liệu tương ứng để xây dựng query
                            """ \
                            + TUDONGNGHIA + \
                            """
                            Lưu ý:
                            - TÊN CÁC BẢNG, CỘT PHẢI ĐỂ TRONG ""
                            - Việc mapping các bảng dựa trên DevelopmentID. Trường DevelopmenID không phải là ModelID. Không được dùng DevelopmenID = ModelID
                            - Bảng GSTD_Model Inventory không có DevelopmentID.
                            - Câu lệnh phải tuân thủ nguyên tắc {dialect} trong Supabase.
                            - Các TRƯỜNG DATE (tên trường có chữ date) phải được chuyển đổi về int với giá trị không null, rồi mới sử dụng. Lưu ý: các trường này có thể tồn tại giá trị NULL hoặc missing.
                            - Bạn phải rà soát câu hỏi người dùng để đảm bảo câu lệnh trả về kết quả chính xác.
                            - Đừng tự thêm điều kiện where mà người dùng không cần
                            - Không thêm ký tự \n, \ không cần thiết.
                            - Các trường text, thực hiện lấy giá trị lowcase để thực hiện điều kiện lọc.
                            - Nếu chủ thể hỏi về mô hình, bạn phải liệt kê thông tin theo DevelopmentID (không phải theo Model ID): ví dụ 
                                số lượng Mô Hình Bán Buôn Cho Doanh Nghiệp Vừa Theo Chuẩn Basel là 02 với DevelopmentID là 32, 33
                            - {previous_error}
                            
                            Bạn chỉ được trả ra câu lệnh query (không thêm bất kỳ thông tin nào khác) mà phải chạy được. Only return the Query, no explanation, no description.
                            Ví dụ: 
                            Đếm số lượng mô hình có loại mô hình là MC ==> câu trả lời đúng là SELECT COUNT(DISTINCT "DevelopmentID") FROM "GSTD_Model Development" d JOIN "GSTD_Model Inventory" i ON d."ModelID" = i."ModelID" WHERE LOWER(i."ModelSegmentation") = LOWER('Doanh nghiệp trung bình')
                            
                            Use the following format:
                            Question: the input question you must answer
                            Thought: you should always think about what to do
                            Action: the action to take, should be one of {tools}
                            Action Input: the input to the action
                            Observation: the result of the action
                            ... (this Thought/Action/Action Input/Observation can repeat 2 times)
                            Thought: I now know the final answer
                            Final Answer: the final answer to the original input question. final answer chỉ là mã lập trình, không được có thêm gì khác. final answer chỉ là mã lập trình, không được có thêm gì khác. 
                            Begin!
                            Question: {question}
                        """

            # Tạo messages với Prompt Caching
            messages = [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": system_prompt.format(
                                input=info_dict["input"],
                                previous_error=info_dict.get("previous_error", ""),
                                question=info_dict["question"]
                            ),
                            "cache_control": {"type": "ephemeral"}  # Cache system prompt
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": user_input
                }
            ]

            # Gọi API Anthropic với Prompt Caching
            response = llm_model.messages.create(
                max_tokens=2000,
                messages=messages,
                model="claude-3-5-sonnet-20241022",
                extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}  # Kích hoạt Prompt Caching
            )

            # Trích xuất SQL từ phản hồi
            def extract_sql_from_final_answer(text):
                """Trích xuất câu SQL từ nội dung chứa 'Final Answer:'"""
                if "Action Input: " in text:
                    _, _, result = text.rpartition("Action Input: ")
                    result = result
                else:
                    result = text
                if "Final Answer:" in result:
                    _, _, result = result.rpartition("Final Answer: ")
                    result = result
                if "Observation" in result:
                    result = result.split("Observation")[0]
                return result.strip()

            final_sql = extract_sql_from_final_answer(response.content[0].text)
            
            return {"query": final_sql}
        
        def execute_query(state):
            """Execute SQL query."""
            print("Câu lệnh để query là ", state["query"])

            db = SQLDatabase.from_uri(SUPABASE_URI)
            

            # return {"result": execute_query_tool.invoke(state["query"])}
            return {"result": pd.DataFrame(db._execute(state["query"]))}
        
        # --------------------------------------------------- fix -----------------------------------------------------------
        def fix_query(query, error_massge, llm_model, info_dict):
            fix_prompt = PromptTemplate.from_template(
                """
                    Bạn là chuyên gia SQL. Một câu truy vấn sau đây đã gặp lỗi:
                    Query: {query}
                    Lỗi: {error_message}
                    
                    Dựa trên thông tin ngữ cảnh: {input}
                    Hãy sửa lại câu truy vấn để nó chạy được trên PostgreSQL (Supabase).
                    Chỉ trả ra câu truy vấn đã sửa, không giải thích.
                """
            )

            chain = fix_prompt | llm_model
            fixed_query = chain.invoke({
                "query": query,
                "error_message": error_message,
                "input": info_dict["input"]
            }).content
            return fixed_query
        
        checker_tool = QuerySQLCheckerTool(db=db, llm=claude)

        # Tạo query và execute
        attempt = 0
        error_message = None
        max_attempts = 3
        info_dict["previous_error"] = ""
        flag_fail = 0
        while attempt <= max_attempts:
            
            result_3 = write_query(anthropic_client, info_dict)
            query = result_3["query"]
            print(f"-------Query ban đầu (attempt {attempt})---------------------------------------: {query}")

            check_result = checker_tool.invoke(query)
            print(f"-------Kết quả kiểm tra---------------------------------------: {check_result}")

            if "Error" not in check_result and "invalid" not in check_result.lower():
                try:
                    result_4 = execute_query(result_3)
                    print(f"-------Query thành công---------------------------------------: {query}")
                    break # Không cần thử đến max_attemp
                except Exception as e:
                    error_message = str(e)
                    print(f"-------QUERY ERROR (attempt {attempt}): {error_message}")
                    result_3["query"] = fix_query(query, error_message, claude, info_dict)
                    info_dict["previous_error"] = f"Lỗi trước đó: {error_message}. Query đã sửa: {query}"
            else:
                error_message = check_result
                print(f"-------CHECKER ERROR (attempt {attempt}): {error_message}")
                result_3["query"] = fix_query(query, error_message, claude, info_dict)
                info_dict["previous_error"] = f"Lỗi cú pháp trước đó: {error_message}. Query đã sửa: {query}"
            
            # Nếu câu lệnh không có lỗi ở trên thì sẽ không đến đoạn này. Đến đây nghĩa là có lỗi
            try:
                result_4 = execute_query(result_3)
                print(f"-------Query đã sửa thành công---------------------------------------: {query}")
                break 
            except Exception as e:
                error_message = str(e)
                print(f"******QUERY ERROR SAU SỬA (attempt {attempt}): {error_message}")
                info_dict["previous_error"] = f"Lỗi sau khi sửa: {error_message}. Query: {query}"
                
                if attempt == max_attempts:
                    st.error(f"Không thể tạo câu truy vấn hợp lệ sau {max_attempts} lần thử. Lỗi cuối cùng: {error_message}")
                    flag_fail = 1
                    break 
                attempt += 1

        # Kết quả sau vòng lặp
        if flag_fail == 0:
            st.write("**Câu lệnh truy vấn dữ liệu**: ", result_3["query"])
            st.dataframe(result_4["result"])
        else:
            st.write("**Phản hồi của Chatbot**: Tôi không tìm thấy được nội dung bạn yêu cầu, bạn có thể làm rõ hơn câu hỏi được không?")
        # ---------------------------------------------fix----------------------------------------------------------------------------------

        ################
        print("-------------------------Kết quả bước 2, Câu lệnh là :-------------------------", result_3["query"])
        if flag_fail == 0:        
            query_copy = copy.deepcopy(result_3["query"])
            st.write("**Câu lệnh truy vấn dữ liệu**: ", query_copy)
            st.dataframe(result_4["result"])

            result_4_copy = copy.deepcopy(result_4["result"])
            import pandas as pd
            
            st.write("**Phản hồi của Chatbot**: ")
            st.dataframe(pd.DataFrame(result_4_copy))
        else:
            st.write("**Phản hồi của Chatbot**: Tôi không tìm thấy được nội dung bạn yêu cầu, bạn có thể làm rõ hơn câu hỏi được không?")


    # VI. Hiển thị:
    def remove_newlines(text):
        return text.replace("\n", "")

    st.write("\n Thời gian thực thi: ", time.time() - start_time)

    st.session_state.chat_history.append({"user": user_input, \
                                                                "bot": "Phản hồi của Chatbot: " + result_3["query"]})

# Hiển thị lịch sử hội thoại
st.subheader(" Lịch sử hội thoại ")
for chat in reversed(st.session_state.chat_history):  
    st.write(f"**Người dùng:** {chat['user']}")
    st.write(f"**Chatbot:** {chat['bot']}")
    st.write(f"**---------**")
