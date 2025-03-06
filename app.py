import os
import time
import json
import copy
import warnings
from typing import TypedDict, Annotated, List
import pandas as pd
import streamlit as st
import copy
from ultis import *
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

# Hàm truy vấn dữ liệu từ Supabase
from functools import lru_cache

def clarify_question(query, chat_history, llm_model):
    def remove_curly_braces(text):
        return text.replace("{", "").replace("}", "")
    
    context = ""
    previous_query = None
    previous_bot_response = None

    if chat_history:
        for chat in reversed(chat_history):
            context += f" Câu hỏi User: {chat['user']} ==> Bot trả lời: {remove_curly_braces(chat['bot'])} \n"
            if previous_query is None: 
                previous_query = chat['user']
                previous_bot_response = chat['bot']
    
    system = DB_SCHEMA_DESCRIPTION + """
    You are a DB assistant. Bạn là chuyên viên phòng mô hình, cẩn thận và chính xác.
    Dựa trên hội thoại trước:
    {context}
    Với câu hỏi hiện tại của User: {question}.
    
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
    
    if "làm rõ hơn" in query.lower() and previous_query:
        human = f"Yêu cầu làm rõ hơn thông tin từ câu hỏi trước: '{previous_query}'. Câu hỏi hiện tại: {query}"
    elif "sai rồi" in query.lower() and previous_bot_response and "SELECT" in previous_bot_response:
        human = f"Yêu cầu sửa lỗi từ câu hỏi trước: '{previous_query}' với câu lệnh SQL trước đó: '{previous_bot_response}'. Câu hỏi hiện tại: {query}"
    else:
        human = "{question}"
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system),
        ("human", human)
    ])

    chain = prompt | llm_model
    tmp = chain.invoke({
        "context": context,
        "question": query
    })
    result = tmp.content
    
    return result


# Giao diện Streamlit
st.title("Model-Inventory AI Chatbot")

# Lưu hội thoại trong session
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Nhập câu hỏi từ người dùng
user_input = st.text_input("Tôi có thể giúp gì cho bạn :")
db = SQLDatabase.from_uri(SUPABASE_URI)

if st.button("Send"):
    if user_input:
        print("===============BẮT ĐẦU===============")
        start_time = time.time()
        # Lưu câu hỏi vào bộ nhớ
        memory.save_context({"input": user_input}, {"output": ""})

        ################ I. Thực thi query SQL từ AI với ngữ cảnh hội thoại ################
        result_1 = clarify_question(user_input, st.session_state.chat_history, claude)
    
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

        def write_query(llm_model, info_dict, error=None):

            prompt = PromptTemplate.from_template(
                (TERM_DES_JSON + """
                    Bạn là chuyên viên phòng mô hình.
                    Bạn là người cẩn thận, chính xác.       
                    Bạn nhận được thông tin các bảng dữ liệu, các trường dữ liệu liên quan là {input}. 
                    Bạn hãy xây dựng câu lệnh query {dialect} cho phù hợp với yêu cầu người dùng. 
                    You have access to the following tools:{tools}

                    Bạn có danh sách các từ sau về thuật ngữ và các trường dữ liệu tương ứng để xây dựng query
                    ------------------------------------
                    CODE = Phân khúc, mô hình => TRƯỜNG
                    Large Corp = Doanh nghiệp lớn => ModelSegmentation
                    LC = Doanh nghiệp lớn => ModelSegmentation
                    Mid Corp = Doanh nghiệp trung bình => ModelSegmentation
                    MC = Doanh nghiệp trung bình => ModelSegmentation
                    FDI = Doanh nghiệp FDI => ModelSegmentation
                    New Corp = Doanh nghiệp mới thành lập => ModelSegmentation
                    NC = Doanh nghiệp mới thành lập => ModelSegmentation
                    Local Bank = Ngân hàng nội địa => ModelSegmentation
                    LB = Ngân hàng nội địa => ModelSegmentation
                    Project Finance = Cấp tín dụng tài trợ dự án => ModelSegmentation
                    PF = Cấp tín dụng tài trợ dự án => ModelSegmentation
                    KHDN = KHDN => ModelSegmentation
                    CORP = KHDN => ModelSegmentation
                    Cho vay không tuần hoàn trong hiệu lực giải ngân = Cho vay không tuần hoàn trong hiệu lực giải ngân và còn hạn mức chưa sử dụng => ModelSegmentation
                    NONR trong hiệu lực giải ngân = Cho vay không tuần hoàn trong hiệu lực giải ngân và còn hạn mức chưa sử dụng => ModelSegmentation
                    NONREVOL trong hiệu lực giải ngân = Cho vay không tuần hoàn trong hiệu lực giải ngân và còn hạn mức chưa sử dụng => ModelSegmentation
                    NONREVOLVING trong hiệu lực giải ngân = Cho vay không tuần hoàn trong hiệu lực giải ngân và còn hạn mức chưa sử dụng => ModelSegmentation
                    Cho vay không tuần hoàn còn hiệu lực giải ngân = Cho vay không tuần hoàn trong hiệu lực giải ngân và còn hạn mức chưa sử dụng => ModelSegmentation
                    NONR còn hiệu lực giải ngân = Cho vay không tuần hoàn trong hiệu lực giải ngân và còn hạn mức chưa sử dụng => ModelSegmentation
                    NONREVOL còn hiệu lực giải ngân = Cho vay không tuần hoàn trong hiệu lực giải ngân và còn hạn mức chưa sử dụng => ModelSegmentation
                    NONREVOLVING còn hiệu lực giải ngân. = Cho vay không tuần hoàn trong hiệu lực giải ngân và còn hạn mức chưa sử dụng => ModelSegmentation
                    REV trong hiệu lực giải ngân = Cho vay tuần hoàn trong hiệu lực giải ngân => ModelSegmentation
                    REVOL trong hiệu lực giải ngân = Cho vay tuần hoàn trong hiệu lực giải ngân => ModelSegmentation
                    REVOLVING trong hiệu lực giải ngân = Cho vay tuần hoàn trong hiệu lực giải ngân => ModelSegmentation
                    
                    REV còn hiệu lực giải ngân = Cho vay tuần hoàn trong hiệu lực giải ngân => ModelSegmentation
                    REVOL còn hiệu lực giải ngân = Cho vay tuần hoàn trong hiệu lực giải ngân => ModelSegmentation
                    REVOLVING còn hiệu lực giải ngân = Cho vay tuần hoàn trong hiệu lực giải ngân => ModelSegmentation
                    TTTM trong hiệu lực giải ngân = TTTM tuần hoàn trong hiệu lực giải ngân => ModelSegmentation
                    TTTM còn hiệu lực giải ngân = TTTM tuần hoàn trong hiệu lực giải ngân => ModelSegmentation
                    CC trong hiệu lực giải ngân = Thẻ tín dụng trong hiệu lực giải ngân => ModelSegmentation
                    CARD trong hiệu lực giải ngân = Thẻ tín dụng trong hiệu lực giải ngân => ModelSegmentation
                    CC còn hiệu lực giải ngân = Thẻ tín dụng trong hiệu lực giải ngân => ModelSegmentation
                    CARD còn hiệu lực giải ngân = Thẻ tín dụng trong hiệu lực giải ngân => ModelSegmentation
                    hết hiệu lực giải ngân = Cho vay tuần hoàn hết hiệu lực giải ngân + Cho vay không tuần hoàn hết hiệu lực giải ngân + Cho vay không tuần hoàn không còn hạn mức tín dụng chưa sử dụng => ModelSegmentation
                    ngoài hiệu lực giải ngân = Cho vay tuần hoàn hết hiệu lực giải ngân + Cho vay không tuần hoàn hết hiệu lực giải ngân + Cho vay không tuần hoàn không còn hạn mức tín dụng chưa sử dụng => ModelSegmentation
                    Normal FDI = FDI thông thường => ModelSegmentation
                    NormalFDI  = FDI thông thường => ModelSegmentation
                    Potential FDI = FDI tiềm năng => ModelSegmentation
                    PotentialFDI = FDI tiềm năng => ModelSegmentation
                    NME = Doanh nghiệp thông thường theo CR => ModelSegmentation
                    MRE = Doanh nghiệp siêu nhỏ theo CR => ModelSegmentation
                    SUE = Doanh nghiệp mới thành lập theo CR => ModelSegmentation
                    KOXH = Doanh nghiệp không xếp hạng => ModelSegmentation
                    Loan TF KHDN = Cho vay + Tài trợ thương mại KHDN => ModelSegmentation
                    Loan TF CORP = Cho vay + Tài trợ thương mại KHDN => ModelSegmentation
                    RSME = Doanh nghiệp Bán lẻ vừa và nhỏ (chỉ bao gồm các khách hàng thuộc quản lý trên Sổ bán buôn) => ModelSegmentation
                    KOXH (PD) = Doanh nghiệp không có xếp hạng theo PD => ModelSegmentation
                    RSME = Doanh nghiệp Bán lẻ vừa và nhỏ => ModelSegmentation
                    PF = Cấp tín dụng tài trợ dự án (PF) => ModelSegmentation
                    OTHSL = Cho vay chuyên biệt khác Tài trợ dự án => ModelSegmentation
                    REV trong hiệu lực giải ngân = Cho vay tuần hoàn trong hiệu lực giải ngân KHDN => ModelSegmentation
                    REVOL trong hiệu lực giải ngân = Cho vay tuần hoàn trong hiệu lực giải ngân KHDN => ModelSegmentation
                    REVOLVING trong hiệu lực giải ngân = Cho vay tuần hoàn trong hiệu lực giải ngân KHDN => ModelSegmentation
                    
                    REV còn hiệu lực giải ngân = Cho vay tuần hoàn trong hiệu lực giải ngân KHDN => ModelSegmentation"
                    REVOL còn hiệu lực giải ngân = Cho vay tuần hoàn trong hiệu lực giải ngân KHDN => ModelSegmentation
                    REVOLVING còn hiệu lực giải ngân = Cho vay tuần hoàn trong hiệu lực giải ngân KHDN => ModelSegmentation
                    CORP CARD = Thẻ tín dụng KHDN => ModelSegmentation
                    CORP CC = Thẻ tín dụng KHDN => ModelSegmentation
                    CARD CORP = Thẻ tín dụng KHDN => ModelSegmentation
                    CC CORP = Thẻ tín dụng KHDN => ModelSegmentation
                    TTTM REVOL trong hiệu lực giải ngân = TTTM tuần hoàn trong hiệu lực giải ngân KHDN => ModelSegmentation
                    TTTM REVOLVING trong hiệu lực giải ngân = TTTM tuần hoàn trong hiệu lực giải ngân KHDN => ModelSegmentation
                    TTTM REV trong hiệu lực giải ngân = TTTM tuần hoàn trong hiệu lực giải ngân KHDN => ModelSegmentation
                    TTTM REVOL còn hiệu lực giải ngân = TTTM tuần hoàn trong hiệu lực giải ngân KHDN => ModelSegmentation
                    TTTM REVOLVING còn hiệu lực giải ngân = TTTM tuần hoàn trong hiệu lực giải ngân KHDN => ModelSegmentation
                    TTTM REV còn hiệu lực giải ngân = TTTM tuần hoàn trong hiệu lực giải ngân KHDN => ModelSegmentation
                    Cho vay không tuần hoàn trong hiệu lực giải ngân = Cho vay không tuần hoàn trong hiệu lực giải ngân KHDN => ModelSegmentation
                    NONR trong hiệu lực giải ngân = Cho vay không tuần hoàn trong hiệu lực giải ngân KHDN => ModelSegmentation
                    NONREVOL trong hiệu lực giải ngân = Cho vay không tuần hoàn trong hiệu lực giải ngân KHDN => ModelSegmentation
                    NONREVOLVING trong hiệu lực giải ngân = Cho vay không tuần hoàn trong hiệu lực giải ngân KHDN => ModelSegmentation
                    Cho vay không tuần hoàn còn hiệu lực giải ngân = Cho vay không tuần hoàn trong hiệu lực giải ngân KHDN => ModelSegmentation
                    NONR còn hiệu lực giải ngân = Cho vay không tuần hoàn trong hiệu lực giải ngân KHDN => ModelSegmentation
                    NONREVOL còn hiệu lực giải ngân = Cho vay không tuần hoàn trong hiệu lực giải ngân KHDN => ModelSegmentation
                    NONREVOLVING còn hiệu lực giải ngân = Cho vay không tuần hoàn trong hiệu lực giải ngân KHDN => ModelSegmentation
                    FB, foreign bank = Ngân hàng nước ngoài => ModelSegmentation
                    NBCI = Tổ chức tín dụng phi ngân hàng => ModelSegmentation
                    NCFI = Định chế tài chính phi tín dụng => ModelSegmentation
                    NCFI - NONREV - LOAN = Định chế tài chính phi tín dụng - Cho vay không tuần hoàn/ tuần hoàn hết hiệu lực giải ngân => ModelSegmentation
                    NCFI NONREV LOAN = Định chế tài chính phi tín dụng - Cho vay không tuần hoàn/ tuần hoàn hết hiệu lực giải ngân => ModelSegmentation
                    NCFI NONREVOLVING LOAN = Định chế tài chính phi tín dụng - Cho vay không tuần hoàn/ tuần hoàn hết hiệu lực giải ngân => ModelSegmentation
                    NCFI LOAN NONREV = Định chế tài chính phi tín dụng - Cho vay không tuần hoàn/ tuần hoàn hết hiệu lực giải ngân => ModelSegmentation
                    NCFI LOANNONREV = Định chế tài chính phi tín dụng - Cho vay không tuần hoàn/ tuần hoàn hết hiệu lực giải ngân => ModelSegmentation
                    NCFI - CARD = Định chế tài chính phi tín dụng - Thẻ tín dụng => ModelSegmentation
                    NCFI CARD = Định chế tài chính phi tín dụng - Thẻ tín dụng => ModelSegmentation
                    NCFI CC = Định chế tài chính phi tín dụng - Thẻ tín dụng => ModelSegmentation
                    NCFI-CC = Định chế tài chính phi tín dụng - Thẻ tín dụng => ModelSegmentation
                    NCFI - REV - LOAN = Định chế tài chính phi tín dụng - Cho vay tuần hoàn trong hiệu lực giải ngân => ModelSegmentation
                    NCFI REV LOAN = Định chế tài chính phi tín dụng - Cho vay tuần hoàn trong hiệu lực giải ngân => ModelSegmentation
                    NCFI REVOLVING LOAN = Định chế tài chính phi tín dụng - Cho vay tuần hoàn trong hiệu lực giải ngân => ModelSegmentation
                    NCFI loanREV; = Định chế tài chính phi tín dụng - Cho vay tuần hoàn trong hiệu lực giải ngân => ModelSegmentation
                    NCFI - TF = Định chế tài chính phi tín dụng - TTTM tuần hoàn/ tuần trong hiệu lực giải ngân => ModelSegmentation
                    NCFI TF = Định chế tài chính phi tín dụng - TTTM tuần hoàn/ tuần trong hiệu lực giải ngân => ModelSegmentation
                    NCFI TTTM = Định chế tài chính phi tín dụng - TTTM tuần hoàn/ tuần trong hiệu lực giải ngân => ModelSegmentation
                    NCFI-TTTM = Định chế tài chính phi tín dụng - TTTM tuần hoàn/ tuần trong hiệu lực giải ngân => ModelSegmentation
                    IB = Cho vay Cá nhân sản xuất kinh doanh => ModelSegmentation
                    ibiz = Cho vay Cá nhân sản xuất kinh doanh => ModelSegmentation
                    SXKD = Cho vay Cá nhân sản xuất kinh doanh => ModelSegmentation
                    RES = Cho vay bất động sản => ModelSegmentation
                    RE = Cho vay bất động sản => ModelSegmentation
                    BĐS = Cho vay bất động sản => ModelSegmentation
                    BDS = Cho vay bất động sản => ModelSegmentation
                    cho vay BĐS = Cho vay bất động sản => ModelSegmentation
                    CSE = Cho vay tiêu dùng có TSBĐ => ModelSegmentation
                    CONSUMER-SE = Cho vay tiêu dùng có TSBĐ => ModelSegmentation
                    CONS = Cho vay tiêu dùng có TSBĐ => ModelSegmentation
                    CVTD có TSBĐ = Cho vay tiêu dùng có TSBĐ => ModelSegmentation
                    cvtd secured = Cho vay tiêu dùng có TSBĐ => ModelSegmentation
                    cho vay SXKD = Cho vay tiêu dùng có TSBĐ => ModelSegmentation
                    CONSUMER-UNSE = Cho vay tiêu dùng không có TSBĐ => ModelSegmentation
                    CUS = Cho vay tiêu dùng không có TSBĐ => ModelSegmentation
                    UNSEC = Cho vay tiêu dùng không có TSBĐ => ModelSegmentation
                    cvtd không tsbđ = Cho vay tiêu dùng không có TSBĐ => ModelSegmentation
                    cvtd unsecured = Cho vay tiêu dùng không có TSBĐ => ModelSegmentation
                    CARD = Thẻ tín dụng => ModelSegmentation
                    CC = Thẻ tín dụng => ModelSegmentation
                    CREDIT CARD = Thẻ tín dụng => ModelSegmentation
                    CAR = Cho vay mua ô tô/ xe máy để tiêu dùng => ModelSegmentation
                    AUTO = Cho vay mua ô tô/ xe máy để tiêu dùng => ModelSegmentation
                    ô tô = Cho vay mua ô tô/ xe máy để tiêu dùng => ModelSegmentation
                    oto = Cho vay mua ô tô/ xe máy để tiêu dùng => ModelSegmentation
                    FX = FX => ModelSegmentation
                    ngoại tệ = FX => ModelSegmentation
                    ngoại hối = FX => ModelSegmentation
                    IRS = IRS => ModelSegmentation
                    interest rate swap = IRS => ModelSegmentation
                    hợp đồng hoán đổi lãi suất = IRS => ModelSegmentation
                    hoán đổi lãi suất. IRS thuộc phái sinh lãi suất (PSLS) = IRS => ModelSegmentation
                    CCS = CCS => ModelSegmentation
                    cross currency swap = CCS => ModelSegmentation
                    hợp đồng hoán đổi ngoại tệ = CCS => ModelSegmentation
                    hoán đổi ngoại tệ. CCS thuộc phái sinh lãi suất (PSLS) = CCS => ModelSegmentation
                    SKD = SKD => ModelSegmentation
                    sổ kinh doanh = SKD => ModelSegmentation
                    trading book = SKD => ModelSegmentation
                    TB = SKD => ModelSegmentation
                    Gold = Gold => ModelSegmentation
                    XAU (thuộc: commodity = Gold => ModelSegmentation
                    giao dịch hàng hóa) = Gold => ModelSegmentation
                    TUNGLAN = Cho vay từng lần => ModelSegmentation
                    NONREVOL = Cho vay từng lần => ModelSegmentation
                    NONREVOLVING = Cho vay từng lần => ModelSegmentation
                    NONR = Cho vay từng lần => ModelSegmentation
                    NONRE = Cho vay từng lần => ModelSegmentation
                    Cho vay hạn mức = Cho vay hạn mức => ModelSegmentation
                    REVOLVING = Cho vay hạn mức => ModelSegmentation
                    REV = Cho vay hạn mức => ModelSegmentation
                    REVOL = Cho vay hạn mức => ModelSegmentation
                    OTH = Cho vay khác => ModelSegmentation
                    cho vay OTH = Cho vay khác => ModelSegmentation
                    CSE = Cho vay tiêu dùng có tài sản bảo đảm => ModelSegmentation
                    CONSUMER-SE = Cho vay tiêu dùng có tài sản bảo đảm => ModelSegmentation
                    CONS = Cho vay tiêu dùng có tài sản bảo đảm => ModelSegmentation
                    CONSUMER-UNSE = Cho vay tiêu dùng không có tài sản bảo đảm => ModelSegmentation
                    CUS = Cho vay tiêu dùng không có tài sản bảo đảm => ModelSegmentation
                    UNSEC = Cho vay tiêu dùng không có tài sản bảo đảm => ModelSegmentation
                    CAR = Cho vay mua ô tô => ModelSegmentation
                    AUTO = Cho vay mua ô tô => ModelSegmentation
                    ô tô = Cho vay mua ô tô => ModelSegmentation
                    oto = Cho vay mua ô tô => ModelSegmentation
                    cho vay ô tô = Cho vay mua ô tô => ModelSegmentation
                    UNRATED = Các khoản vay không được xếp hạng => ModelSegmentation
                    UNRATE = Các khoản vay không được xếp hạng => ModelSegmentation
                    UNRATED LOAN = Các khoản vay không được xếp hạng => ModelSegmentation
                    UNRATE LOAN = Các khoản vay không được xếp hạng => ModelSegmentation
                    khoản vay UNRATE = Các khoản vay không được xếp hạng => ModelSegmentation
                    khoản vay UNRATED = Các khoản vay không được xếp hạng => ModelSegmentation
                    LoanRevCardODTF = Cho vay tuần hoàn, thẻ tín dụng và sản phẩm thấu chi, tài trợ thương mại => ModelSegmentation
                    BEEL KHCN = Khoản vay đã vỡ nợ phân khúc KHCN => ModelSegmentation
                    BB = Khách hàng bán buôn => ModelSegmentation
                    RRTD_BB = Khách hàng bán buôn => ModelSegmentation
                    SME = Doanh nghiệp Bán lẻ vừa và nhỏ (chỉ bao gồm các khách hàng thuộc quản lý trên Sổ bán lẻ) => ModelSegmentation
                    Deposit Loan Repo  = Deposit Loan Repo => ModelSegmentation
                    MBF = Mô hình sử dụng dữ liệu thay thế  => ModelSegmentation
                    MobiFone = Mô hình sử dụng dữ liệu thay thế  => ModelSegmentation
                    Alternative data = Mô hình sử dụng dữ liệu thay thế  => ModelSegmentation
                    alternative = Mô hình sử dụng dữ liệu thay thế  => ModelSegmentation
                    BL = Khách hàng Bán lẻ => ModelSegmentation
                    Retail = Khách hàng Bán lẻ => ModelSegmentation
                    TPCP = Định giá sản phẩm Giấy tờ có giá do Kho bạc Nhà nước phát hành => ModelName
                    GOV BOND = Định giá sản phẩm Giấy tờ có giá do Kho bạc Nhà nước phát hành => ModelName
                    TPCPBL/ CQDP = Định giá sản phẩm Giấy tờ có giá được Chính phủ bảo lãnh/Chính quyền địa phương phát hành => ModelName
                    TPCPBL = Định giá sản phẩm Giấy tờ có giá được Chính phủ bảo lãnh/Chính quyền địa phương phát hành => ModelName
                    CQDP = Định giá sản phẩm Giấy tờ có giá được Chính phủ bảo lãnh/Chính quyền địa phương phát hành => ModelName
                    TPCPBL CQDP = Định giá sản phẩm Giấy tờ có giá được Chính phủ bảo lãnh/Chính quyền địa phương phát hành => ModelName
                    Mô hình định giá Bond FI = Mô hình Định giá GTCG do TCTD phát hành => ModelName
                    Mô hình định giá  FI Bond = Mô hình Định giá GTCG do TCTD phát hành => ModelName
                    mô hình MtM = Mô hình định giá IRS VND => ModelName
                    mô hình MTM = Mô hình định giá IRS VND => ModelName
                    mô hình mark to market = Mô hình định giá IRS VND => ModelName
                    mô hình USD SOFR ON = Mô hình định giá IRS USD tham chiếu SOFR ON => ModelName
                    mô hình USD SOFRON = Mô hình định giá IRS USD tham chiếu SOFR ON => ModelName
                    mô hình USD SOFR = Mô hình định giá IRS USD tham chiếu Term SOFR => ModelName
                    mô hình USDR TERM SOFR = Mô hình định giá IRS USD tham chiếu Term SOFR => ModelName
                    mô hình CCS SOFR ON = Mô hình định giá CCS USD/VND với chân USD thả nổi tham chiếu SOFR ON daily compounded in Arrears => ModelName
                    mô hình CCS SOFR = Mô hình định giá CCS USD/VND với chân USD thả nổi tham chiếu Term SOFR => ModelName
                    mô hình Var FX = Mô hình VaR cho danh mục kinh doanh ngoại tệ => ModelName
                    mô hình Var FX SKD = Mô hình VaR cho danh mục kinh doanh ngoại tệ => ModelName
                    mô hình Var FX tự doanh = Mô hình VaR cho danh mục kinh doanh ngoại tệ => ModelName
                    mô hình VaR GTCG = Mô hình VaR lịch sử GTCG => ModelName
                    mô hình VaR Bond = Mô hình VaR lịch sử GTCG => ModelName
                    mô hình VaR PSLS = Mô hình VaR phái sinh lãi suất => ModelName
                    mô hình VaR tổng = Mô hình VaR tổng Sổ kinh doanh => ModelName
                    mô hình VaR.Total = Mô hình VaR tổng Sổ kinh doanh => ModelName
                    mô hình Var total = Mô hình VaR tổng Sổ kinh doanh => ModelName
                    MTM GOLD = Mô hình định giá danh mục vàng miếng tại VCB => ModelName
                    Add-on FX JPY/VND = Mô hình định giá cho các giao dịch kinh doanh ngoại hối đối với cặp JPY/VND kỳ hạn trên 1 năm đến 2 năm => ModelName
                    Add on FX JPY VND = Mô hình định giá cho các giao dịch kinh doanh ngoại hối đối với cặp JPY/VND kỳ hạn trên 1 năm đến 2 năm => ModelName
                    Addon FX JPY/VND = Mô hình định giá cho các giao dịch kinh doanh ngoại hối đối với cặp JPY/VND kỳ hạn trên 1 năm đến 2 năm => ModelName
                    Addon FX JPY-VND = Mô hình định giá cho các giao dịch kinh doanh ngoại hối đối với cặp JPY/VND kỳ hạn trên 1 năm đến 2 năm => ModelName
                    MtM FI BOND CP 1Y = Mô hình định giá GTCG do TCTD phát hành có quyền chọn call put đồng thời kỳ hạn từ 1 năm trở xuống trên sổ kinh doanh	 => ModelName
                    MtM FI BOND call put 1Y = Mô hình định giá GTCG do TCTD phát hành có quyền chọn call put đồng thời kỳ hạn từ 1 năm trở xuống trên sổ kinh doanh	 => ModelName
                    MtM GTCG SNH = Mô hình định giá giao dịch GTCG TCTD SNH => ModelName
                    MtM GTCG BB = Mô hình định giá giao dịch GTCG TCTD SNH => ModelName
                    MtM GTCG ALM = Mô hình định giá giao dịch GTCG TCTD SNH => ModelName
                    MtM CPCP USD SNH = Mô hình định giao dịch TPCP USD SNH => ModelName
                    mô hình Var FI Bond = Mô hình VaR lịch sử GTCG do TCTD phát hành => ModelName
                    mô hình Var Bond FI = Mô hình VaR lịch sử GTCG do TCTD phát hành => ModelName
                    Cho vay không tuần hoàn còn có thể giải ngân = Cho vay không tuần hoàn trong hiệu lực giải ngân và còn hạn mức chưa sử dụng => ModelSegmentation
                    NONR còn có thể giải ngân = Cho vay không tuần hoàn trong hiệu lực giải ngân và còn hạn mức chưa sử dụng => ModelSegmentation
                    NONREVOL còn có thể giải ngân = Cho vay không tuần hoàn trong hiệu lực giải ngân và còn hạn mức chưa sử dụng => ModelSegmentation
                    NONREVOLVING còn có thể giải ngân = Cho vay không tuần hoàn trong hiệu lực giải ngân và còn hạn mức chưa sử dụng => ModelSegmentation
                    I9 = IFRS9 => RegulatoryCompliance
                    Cho vay tuần hoàn = Cho vay hạn mức => ModelSegmentation
                    Cho vay không tuần hoàn = Cho vay từng lần => ModelSegmentation
                    ------------------------------------
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
                    
                    Use the following format:
                    Question: the input question you must answer
                    Thought: you should always think about what to do
                    Action: the action to take, should be one of {tools}
                    Action Input: the input to the action
                    Observation: the result of the action
                    ... (this Thought/Action/Action Input/Observation can repeat maximum 2 times)
                    Thought: I now know the final answer
                    Final Answer: the final answer to the original input question. final answer chỉ là mã lập trình, không được có thêm gì khác. final answer chỉ là mã lập trình, không được có thêm gì khác. 
                    
                    Begin!
                    Question: {question}
                """)
            )

            # Format prompt với dữ liệu thực tế
            formatted_prompt = prompt.format(
                dialect="PostgreSQL",
                question=info_dict["question"],
                input=info_dict["input"],
                previous_error = info_dict["previous_error"],
                tools= """["QuerySQLDatabaseTool", "InfoSQLDatabaseTool", "ListSQLDatabaseTool", "QuerySQLCheckerTool"]"""
            )

            # Tạo Agent Executor (Dùng Prompt ĐÃ FORMAT)
            agent_executor = create_react_agent(llm_model, tools, prompt=formatted_prompt)
            answer = agent_executor.invoke({"messages": [{"role": "user", "content": info_dict["question"]}]})

            def extract_sql_from_final_answer(text):
                print("text truoc khi extract", text)
                print("end")
                                
                if "Action Input: " in text:   
                    _, _, result = text.rpartition("Action Input: ")
                    result =  result
                else: 
                    result = text
                if "Final Answer:" in result:
                    _, _, result = result.rpartition("Final Answer: ")
                    result =  result
                if "Observation" in result:
                    result = result.split("Observation")[0]
                return result

            final_sql = extract_sql_from_final_answer(answer["messages"][1].content)
            return {"query": final_sql}
        
        def execute_query(state):
            
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
        flag_success = 0
        
        while attempt <= max_attempts:

            result_3 = write_query(claude, info_dict)
            query = result_3["query"]
            check_result = checker_tool.invoke(query)

            if "Error" not in check_result and "invalid" not in check_result.lower():
                try:
                    result_4 = execute_query(result_3)
                    flag_success = 1
                    break
                except Exception as e:
                    error_message = str(e)
                    query = fix_query(query, error_message, claude, info_dict)
                    info_dict["previous_error"] = f"Lỗi trước đó: {error_message}. Query đã sửa: {query}"
            else:
                error_message = check_result
                query = fix_query(query, error_message, claude, info_dict)
                info_dict["previous_error"] = f"Lỗi cú pháp trước đó: {error_message}. Query đã sửa: {query}"

            result_3["query"] = query       
            if flag_success == 0: # nếu câu lệnh đã được sửa thì thực hiện chạy lại.
                try:
                    result_4 = execute_query(result_3)
                    flag_success == 1
                    break 
                except Exception as e:
                    error_message = str(e)
                    info_dict["previous_error"] = f"Lỗi sau khi sửa: {error_message}. Query: {query}"

                    if attempt == max_attempts:
                        st.error(f"Không thể tạo câu truy vấn hợp lệ sau {max_attempts} lần thử. Lỗi cuối cùng: {error_message}")
                        flag_fail = 1
                        break 
                    attempt += 1
        st.write(" Hoàn thành kiểm tra CSDL. ")
        
        if flag_fail == 0:        
            query_copy = copy.deepcopy(result_3["query"])
            st.write("**Câu lệnh truy vấn dữ liệu**: ", query_copy)
            st.write("**Phản hồi của Chatbot**: Kết quả như sau")
            st.dataframe(pd.DataFrame(result_4["result"]))
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