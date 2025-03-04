import os
import time
import json
import copy
import warnings
from typing import TypedDict, Annotated, List

import streamlit as st

from ultis import *

# from langchain.chat_models import ChatOpenAI, init_chat_model
from langchain.memory import ConversationBufferMemory
from langchain.sql_database import SQLDatabase
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain.schema import HumanMessage
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langgraph.prebuilt import create_react_agent

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
# claude = ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0.7)
# openai = init_chat_model("gpt-4")
openai = ChatOpenAI(model_name="gpt-4")
claude = init_chat_model("claude-3-5-sonnet-20241022")

# Tạo bộ nhớ hội thoại
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, k = 5)

# Hàm truy vấn dữ liệu từ Supabase
def clarify_question(query, chat_history, llm_model):

    def remove_curly_braces(text):
        return text.replace("{", "").replace("}", "")
    
    context = "\n".join([f"Câu hỏi User: {chat['user']} ==> Bot hiểu yêu cầu như sau: {remove_curly_braces(chat['bot'])}" \
                         for chat in chat_history])
    print("== LỊCH SỬ CONTEXT: == \n", context)
    system = DB_SCHEMA_DESCRIPTION \
    + """You are a DB assistant. Dựa trên hội thoại trước: """ + context \
    + """Với câu hỏi hiện tại của User: {question}. """ \
    + """ 
    Nhiệm vụ của bạn là:
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
        result_1 = clarify_question(user_input, st.session_state.chat_history, claude)
        
        print("-------------------------Kết quả bước 1: -------------------------\n", result_1)

        # tách thông tin từ kết quả trả về
        if isinstance(result_1, dict):
            print("result_1 đã là dictionary, không cần json.loads()")
        else:
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
        from langchain_community.agent_toolkits import SQLDatabaseToolkit
        from typing_extensions import Annotated
        toolkit = SQLDatabaseToolkit(db=db, llm=claude)
        tools = toolkit.get_tools()

        from langgraph.prebuilt import create_react_agent
        info_dict["error"] = None

        def write_query(llm_model, info_dict, error=None):

            prompt = PromptTemplate.from_template(
                (TERM_DES_JSON + """
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
                    Ví dụ: 
                    Đếm số lượng mô hình có loại mô hình là MC ==> câu trả lời đúng là SELECT COUNT(DISTINCT "DevelopmentID") FROM "GSTD_Model Development" d JOIN "GSTD_Model Inventory" i ON d."ModelID" = i."ModelID" WHERE LOWER(i."ModelSegmentation") = LOWER('Doanh nghiệp trung bình')
                    
                    Use the following format:
                    Question: the input question you must answer
                    Thought: you should always think about what to do
                    Action: the action to take, should be one of {tools}
                    Action Input: the input to the action
                    Observation: the result of the action
                    ... (this Thought/Action/Action Input/Observation can repeat N times)
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
                """Trích xuất câu SQL từ nội dung chứa 'Final Answer:'"""
                st.write("------------------------------ text la  ", text)
                if "Action Input: " in text:   
                    _, _, result = text.rpartition("Action Input: ")
                    result =  result.strip()
                if "Final Answer:" in result:
                    _, _, result = result.rpartition("Final Answer: ")
                    result =  result.strip()
                if "Observation" in result:
                    result = result.split("Observation")[0].strip()
                return result

            final_sql = extract_sql_from_final_answer(answer["messages"][1].content)
            st.write("------------------------------ final_sql bat dau ", final_sql)
            st.write("------------------------------ ket thuc ", final_sql)
            print("------------------------------ final_sql", final_sql)
            return {"query": final_sql}
        
        def execute_query(state):
            """Execute SQL query."""
            print("Câu lệnh để query là ", state["query"])
            return {"result": execute_query_tool.invoke(state["query"])}

        # Tạo query và execute
        attempt = 0
        error_message = None
        max_attempts = 5
        info_dict["previous_error"] = ""

        while attempt <= max_attempts:
            result_3 = write_query(claude, info_dict)                
            print("-------result_3 là ", result_3)
            try:
                # Execute query
                result_4 = execute_query(result_3)
                break  # Nếu thành công, thoát khỏi vòng lặp
            except Exception as e:
                error_message = str(e)
                print(f"******QUERY ERROR (attempt {attempt}): Việc tạo Query xuất hiện lỗi: {error_message}")
                st.write(f"QUERY ERROR (attempt {attempt}): Việc tạo Query xuất hiện lỗi: {error_message}")
                
                # Update info_dict with error information for better context
                info_dict["previous_error"] = "Hãy phân tích để phát hiện lỗi và tránh lỗi từ truy vấn sau: " + result_3["query"] + ". Câu truy vấn này đã gặp lỗi: " + error_message
                if attempt == max_attempts:
                    st.error(f"Không thể tạo câu truy vấn hợp lệ sau {max_attempts} lần thử. Lỗi cuối cùng: {error_message}")
                    break  # Dừng vòng lặp ngay

                attempt += 1
        # If we've exhausted all attempts
        

        ################
        print("-------------------------Kết quả bước 2, Câu lệnh là :-------------------------", result_3["query"])
        st.write("**Câu lệnh truy vấn dữ liệu**: ", result_3["query"])
        st.write("**Kết quả truy vấn**: ", result_4["result"])

        # V. Trả lời
        def generate_answer(state, model):
            """Answer question using retrieved information as context."""
            prompt = (
                """
                Given the following user question, corresponding query, 
                and db retrieval result, answer the user question.\n\n
                Question: {}

                Result provided: {}

                Câu trả lời cần liệt kê các thông tin liên quan tới định danh như DevelopmentID (không được cắt, bỏ thông tin)
                
                Trình bày đẹp, bỏ các ký tự \n đi
                """.format(state["question"], state["result"])
            )
            response = model.invoke(prompt)
            return response.content

        result_5 = generate_answer({"question":clarified_question, "result": result_4 }, openai)
        print("-------------------------Kết quả bước 5, final answer :-------------------------", result_5)
        st.write("**Phản hồi của Chatbot**: ", result_5)


    # VI. Hiển thị:
    def remove_newlines(text):
        return text.replace("\n", "")

    # response_text = "1. Câu hỏi làm rõ: " + clarified_question +  "----" +  "\n 2. Câu lệnh query: " + result_3["query"] +  "----" +  "\n 3. Kết quả:  " + str(result_5)
    # response_text = remove_newlines(response_text)
    st.write("\n Thời gian thực thi: ", time.time() - start_time)
    
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
                                                                "bot": "Phản hồi của Chatbot: " + result_3["query"]})

# Hiển thị lịch sử hội thoại
st.subheader(" Lịch sử hội thoại ")
for chat in reversed(st.session_state.chat_history):  
    st.write(f"**Người dùng:** {chat['user']}")
    st.write(f"**Chatbot:** {chat['bot']}")
    st.write(f"**---------**")
