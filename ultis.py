import os
import getpass
import streamlit as st

from sqlalchemy import create_engine
from typing_extensions import Annotated

from langchain import hub
from langchain.chat_models import init_chat_model
from langchain_experimental.sql import SQLDatabaseChain
# from langchain.utilities import SQLDatabase
from langchain_community.utilities import SQLDatabase

# Comment out the below to opt-out of using LangSmith in this notebook. Not required.
os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
SUPABASE_URI = st.secrets["SUPABASE_URI"]
os.environ["LANGSMITH_TRACING"] = st.secrets["LANGSMITH_TRACING"]
os.environ["LANGSMITH_ENDPOINT"] = st.secrets["LANGSMITH_ENDPOINT"]
os.environ["LANGSMITH_API_KEY"] = st.secrets["LANGSMITH_API_KEY"]
os.environ["LANGSMITH_PROJECT"] = st.secrets["LANGSMITH_PROJECT"]
os.environ["LANGCHAIN_ENDPOINT"] = st.secrets["LANGCHAIN_ENDPOINT"]

DB_SCHEMA_DESCRIPTION = """
Để hỗ trợ bạn trả lời các câu hỏi trên, tôi đã cung cấp cho bạn một số thông tin cần thiết:
- Bảng "GSTD_Model Inventory" chứa thông tin về tên, phân loại, phân khúc mô hình, mã định danh mô hình, gồm các trường:
ModelID: mã định danh mô hình, hoặc mã mô hình. 
ModelIDCharacter: tên mô hình theo QLRRTH
ModelName: tên mô hình
RiskType_lv1: phân loại model theo loại rủi ro cấp 1, bao gồm các nhóm như RRTD (rủi ro tín dụng), RRTT (rủi ro thị trường), RRHĐ (rủi ro hoạt động),... 
RiskType_lv2: phân loại model theo loại rủi ro cấp 2, dựa theo RiskType_lv1 nhưng chi tiết hơn, như RRTD bán buôn, RRTD bán lẻ, RRTT, RRTD đối tác, RRLSTSNH, RR thanh khoản, RRHĐ, ...
RiskParameter: phân loại model theo tham số rủi ro như: XHTD CR, PD, LGD, EAD, BEEL, LGD-in-default, …
ModelSegmentation: phân khúc mô hình hướng tới. 

- Bảng "GSTD_Model Development" lưu trữ thông tin về quá trình phát triển, xây dựng mô hình. 
DevelopmentID: mã phát triển, mã xây dựng mô hình. 
ModelID: mã mô hình. DevelopmentID: mã phát triển, mã xây dựng mô hình
ModelVersion: Phiên bản của mô hình 
ModelDevelopmentUnit: đơn vị hoặc bộ phận xây dựng mô hình. 
MBO: MBO của mô hình
AuthorityApproval: cấp thẩm quyền phê duyệt, gồm cấp HĐQT, CEO, CRO, EBO.
LifecycleStage: trạng thái hiện tại của model trong vòng đời. 
DevelopmentDate: ngày phê duyệt kết quả XDMH, format text  'YYYYMMDD' (lưu ý dạng text, không phải date hay int) 
TerminationDate: ngày phê duyệt dừng ứng dụng. Nếu mô hình chưa ứng dụng, trường để trống.
ModelStatus: Trạng thái hiệu lực của mô hình

- Bảng GSTD_Model Compliance: thông tin việc tuân thủ các quy định và tiêu chuẩn như Basel, IFRS9, v.v. Bảng quan trọng để theo dõi xem mô hình được phát triển theo quy định, tiêu chuẩn nào
ComplianceID: trường định danh, giúp nhận diện từng trường hợp tuân thủ. 
DevelopmentID: trường định danh, tương tự các bảng khác. 
RegulatoryCompliance: thông tin tiêu chuẩn, quy định phải tuân thủnhư Basel II, Basel III, IFRS9, v.v

- GSTD_Model Audit: Thông tin liên quan tới kiểm toán. Các trường dữ liệu gồm:
AuditID: Định danh duy nhất của kết quả kiểm toán mô hình
DevelopmentID: trường định danh, tương tự các bảng khác.
ModelAuditUnit: Bộ phận thực hiện kiểm toán 
AuditDate: Ngày phê duyệt kết quả kiểm toán

- GSTD_Model Implementation: bảng liên quan tới triển khai, tin học hóa. Các trường gồm:
DevelopmentID: trường định danh, tương tự các bảng khác.
ImplementationID: Định danh duy nhất của triển khai
ImplementationType: Hình thức tin học hóa, triển khai 
ImplementationDate: Ngày phê duyệt kết quả triển khai 

- GSTD_Model Monitoring: bảng liên quan tới GSMH. Các trường gồm:
DevelopmentID: trường định danh, tương tự các bảng khác.
MonitoringID: Định danh duy nhất của kết quả GSMH
MonitoringType: phân loại Giám sát định kì hay giám sát đột xuất
MonitoringDate: Ngày phê duyệt kết quả GSMH
MonitoringReportDate:Ngày hoàn thành dự thảo báo cáo giám sát

- GSTD_Model Risk Rating: bảng về tới xếp hạng rủi ro (XHRRMH). Các trường gồm. 
DevelopmentID: trường định danh, tương tự các bảng khác.
RiskRatingID: Định danh duy nhất của kết quả XHRRMH
RatingStage: Xếp hạng rủi ro xác định trong giai đoạn nào của vòng đời
RatingDate: Ngày thực hiện XHRRMH
ModelRiskRating: Kết quả xếp hạng RRMH.

- GSTD_Model Usage: bảng về ứng dụng. các trường gồm: 
DevelopmentID: trường định danh, tương tự các bảng khác.
UsageID: Định danh duy nhất của ứng dụng 
ApplicationPurpose: Mục đích ứng dụng
MBO: MBO tương ứng với mục đích ứng dụng
UsageFrequency, UsageStartDate, UsageEndDate lần lượt là: Tần suất ứng dụng, Ngày bắt đầu ứng dụng, Ngày dừng ứng dụng

- GSTD_Model Validation: bảng về kiểm định (không phải kiểm toán). Các trường gồm: 
DevelopmentID: trường định danh, tương tự các bảng khác.
ValidationID: Định danh duy nhất của kết quả kiểm định mô hình (KĐMH)
ValidationType: loại Kiểm định (lần đầu, định kì, đột xuất)
ModelValidationUnit: Bộ phận thực hiện KĐMH
ValidationDate: Ngày phê duyệt kết quả kiểm định
ValidationConclusion: Kết luận kiểm định

- GSTD_Model Recommendations: thông tin liên quan khuyến nghị, ghi nhận (các nội dung cần cải thiện). các cột gồm: 
DevelopmentID: trường định danh, tương tự các bảng khác.
RecommendationID:Định danh duy nhất của khuyến nghị 
ProposedUnit:Bộ phận đưa ra vấn đề, ghi nhận
FindingStage: vấn đề phát hiện trong giai đoạn nào vòng đời
Description: Mô tả khuyến nghị 
DueDate: Thời hạn thực hiện chính thức
RecommendationStatus: Trạng thái khuyến nghị ví dụ như chưa thực hiện hay đã thực hiện. 
"""

FULL_DES_JSON ={
  "GSTD_Model Inventory": {
    "description": "GSTD_Model Inventory chứa thông tin về tên, phân loại, phân khúc mô hình, mã định danh mô hình, gồm các trường:",
    "fields": {
      "ModelID": "Mã định danh mô hình, hoặc mã mô hình.",
      "ModelIDCharacter": "Tên mô hình theo QLRRTH.",
      "ModelName": "Tên mô hình",
      "RiskType_lv1": "Phân loại model theo loại rủi ro cấp 1, bao gồm các nhóm như RRTD (rủi ro tín dụng), RRTT (rủi ro thị trường), RRHĐ (rủi ro hoạt động)",
      "RiskType_lv2": "Phân loại model theo loại rủi ro cấp 2, dựa theo RiskType_lv1 nhưng chi tiết hơn, ví dụ: RRTD bán buôn, RRTD bán lẻ, RRLSTSNH, RRTT, RRTD đối tác.",
      "RiskParameter": "Phân loại model theo tham số rủi ro ví dụ: PD, Supervisory slot, LGD, EAD, XHTD CR, EWS, BEEL, Hành vi tiền gửi KKH, Hành vi tiền vay, Hành vi tiền gửi có kì hạn, Định giá, Value-at-Risk, Add on, Stress test, Khác.",
      "ModelSegmentation": "Phân khúc mô hình hướng tới."
    }
  },
  "GSTD_Model Development": {
    "description": "GSTD_Model Development lưu trữ thông tin về quá trình phát triển, xây dựng mô hình.",
    "fields": {
      "DevelopmentID": "Mã phát triển, mã xây dựng mô hình.",
      "ModelID": "Mã mô hình.",
      "ModelDevelopmentUnit": "Đơn vị, bộ phận xây dựng model, ví dụ: Tư vấn Oliver Wyman, Phòng Quant, Phòng QLRRTT, Tư vấn BCG, Phòng ALM.",
      "MBO": "MBO của mô hình, ví dụ: QLRRTD, Công nợ, QLRRTT, ALM.",
      "AuthorityApproval": "Cấp thẩm quyền phê duyệt, gồm cấp HĐQT, CEO, CRO, EBO.",
      "LifecycleStage": "Trạng thái hiện tại của model trong vòng đời, ví dụ: Ứng dụng mô hình, Triển khai mô hình, Phê duyệt mô hình, Kiểm định mô hình lần đầu, Đã hoàn thành triển khai nhưng chưa ứng dụng, Xây dựng mô hình.",
      "DevelopmentDate": "Ngày phê duyệt kết quả XDMH, format text  'YYYYMMDD' (lưu ý dạng text, không phải date hay int).",
      "TerminationDate": "Ngày phê duyệt dừng ứng dụng. Nếu mô hình chưa ứng dụng, trường để trống.",
      "ModelStatus": "Trạng thái hiệu lực của mô hình, ví dụ: Đang hiệu lực, Chưa hiệu lực, Hết hiệu lực."
    }
  },
  "GSTD_Model Implementation": {
    "description": "GSTD_Model Implementation: Bảng liên quan tới triển khai, tin học hóa.",
    "fields": {
      "ImplementationType": "Hình thức tin học hóa, triển khai, ví dụ: Tin học hóa toàn bộ bởi Bộ phận CNTT, Tin học hóa bởi Đơn vị thuê ngoài, Tin học hóa toàn bộ bởi Bộ phận XDMH.",
      "DevelopmentID": "trường định danh, tương tự các bảng khác.",
      "ImplementationID": "Định danh duy nhất của triển khai",
      "ImplementationDate": "Ngày phê duyệt kết quả triển khai"
    }
  },
  "GSTD_Model Monitoring": {
    "description": "GSTD_Model Monitoring: Bảng liên quan tới GSMH.",
    "fields": {
      "MonitoringType": "Phân loại Giám sát ví dụ: Giám sát đột xuất, Giám sát định kì.",
      "MonitoringDate": "Ngày phê duyệt kết quả GSMH.",
      "MonitoringReportDate": "Ngày hoàn thành dự thảo báo cáo giám sát.",
      "DevelopmentID": "Trường định danh, tương tự các bảng khác.",
      "MonitoringID": "Định danh duy nhất của kết quả GSMH."
    }
  },
  "GSTD_Model Risk Rating": {
    "description": "GSTD_Model Risk Rating: Bảng về tới xếp hạng rủi ro (XHRRMH).",
    "fields": {
      "DevelopmentID": "Trường định danh, tương tự các bảng khác.",
      "RiskRatingID": "Định danh duy nhất của kết quả XHRRMH.",
      "RatingStage": "Xếp hạng rủi ro xác định trong giai đoạn nào của vòng đời, ví dụ: Xây dựng mô hình, Giám sát mô hình, Kiểm định mô hình.",
      "RatingDate": "Ngày thực hiện XHRRMH.",
      "ModelRiskRating": "Kết quả xếp hạng RRMH, ví dụ: Cao, Trung bình, Thấp."
    }
  },
  "GSTD_Model Usage": {
    "description": "GSTD_Model Usage: Bảng về ứng dụng.",
    "fields": {
        "DevelopmentID": "Trường định danh, tương tự các bảng khác.",
      "UsageID": "Định danh duy nhất của ứng dụng.",
      "ApplicationPurpose": "Mục đích ứng dụng.",
      "MBO": "MBO tương ứng với mục đích ứng dụng, ví dụ: QLRRTD, Công nợ, PTSPBL, QLRRTT.",
      "UsageFrequency": "Tần suất ứng dụng, ví dụ: Hàng ngày, Hàng quý, Khác, Hàng tháng, Hàng năm.",
      "UsageStartDate": "Ngày bắt đầu ứng dụng.",
      "UsageEndDate": "Ngày dừng ứng dụng."
    }
  },
  "GSTD_Model Validation": {
    "description": "GSTD_Model Validation: Bảng về kiểm định (không phải kiểm toán).",
    "fields": {
        
      "DevelopmentID": "Trường định danh, tương tự các bảng khác.",
      "ValidationID": "Định danh duy nhất của kết quả kiểm định mô hình (KĐMH).",
      "ValidationType": "Loại Kiểm định ví dụ: Kiểm định lần đầu, Kiểm định định kì, Kiểm định đột xuất.",
      "ModelValidationUnit": "Bộ phận thực hiện KĐMH, ví dụ: Tổ kiểm định độc lập, Phòng QLRRTH, Tư vấn EY, Tư vấn BCG.",
      "ValidationDate": "Ngày phê duyệt kết quả kiểm định.",
      "ValidationConclusion": "Kết luận kiểm định, ví dụ: Loại 2, Loại 3, Loại 1."
    }
  },

  "GSTD_Model Recommendations": {
    "description": "GSTD_Recommendations: Thông tin liên quan khuyến nghị, ghi nhận (các nội dung cần cải thiện).",
    "fields": {
       "DevelopmentID": "Trường định danh, tương tự các bảng khác.",
      "RecommendationID": "Định danh duy nhất của khuyến nghị.",
      "ProposedUnit": "Bộ phận đưa ra vấn đề, ghi nhận, ví dụ: Phòng QLRRTH, Phòng Quant, Tư vấn EY, Phòng KToNB, Tổ kiểm định độc lập.",
      "FindingStage": "Vấn đề phát hiện trong giai đoạn nào vòng đời, ví dụ: Giám sát mô hình, Kiểm định mô hình, Kiểm toán mô hình, Xây dựng mô hình.",
      "Description": "Mô tả khuyến nghị.",
      "DueDate": "Thời hạn thực hiện chính thức.",
      "RecommendationStatus": "Trạng thái khuyến nghị ví dụ như chưa thực hiện hay đã thực hiện."
    }
  },
  "GSTD_Model Compliance": {
    "description": "GSTD_Model Compliance: thông tin về việc tuân thủ các quy định và tiêu chuẩn như Basel, IFRS9, v.v. Bảng này giúp theo dõi xem mô hình được phát triển theo quy định, tiêu chuẩn nào.",
    "fields": {
      "ComplianceID": "Trường định danh, giúp nhận diện từng trường hợp tuân thủ",
      "DevelopmentID": "Trường định danh, tương tự các bảng khác",
      "RegulatoryCompliance": "Thông tin tiêu chuẩn, quy định phải tuân thủ như Basel, IFRS9, Thông tư 41/2016/TT-NHNN. Dữ liệu ở dạng list (một mô hình có thể có nhiều tiêu chuẩn, ví dụ ['Basel II RRTD - FIRB','Basel II RRTD - AIRB','IFRS9']) "
    }
  },
  "GSTD_Model Audit": {
    "description": "GSTD_Model Audit: Thông tin liên quan đến kiểm toán mô hình, giúp đánh giá mức độ phù hợp và chính xác của mô hình theo tiêu chuẩn nội bộ và bên ngoài.",
    "fields": {
        
      "AuditID": "Định danh duy nhất của kết quả kiểm toán mô hình.",
      "DevelopmentID": "Trường định danh, tương tự các bảng khác.",
      "ModelAuditUnit": "Bộ phận thực hiện kiểm toán mô hình, ví dụ: Kiểm toán nội bộ, EY, Deloitte.",
      "AuditDate": "Ngày phê duyệt kết quả kiểm toán."
    }
  }
}

GENERAL_DB_QUERY_PROMPT = """
 
        You are an agent designed to interact with a subpabase database.
        Given an input question, create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer.
        Unless the user specifies a specific number of examples to obtain, always limit your query to at most {top_k} results.
        Never query for all the columns from a specific table, only ask for the relevant columns given the question.
        You have access to tools for interacting with the database.
        Only use the below tools. Only use the information returned by the below tools to construct your final answer.
        You MUST double check your query before executing it. If you get an error while executing a query, rewrite the query and try again.
        DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.
"""
TERM_DES_JSON = """
Thuật ngữ: 
        -	HĐQT: Hội đồng quản trị
        -	RRTT: rủi ro thị trường, RRTD: rủi ro tín dụng, RRHĐ: rủi ro hoạt động
        -	KHDN: Nhóm phân khúc khách hàng doanh nhiệp (hay được gọi là bán buôn), RiskType_lv2 = RRTD bán buôn
        -	KHCN: Nhóm phân khúc khách hàng cá nhân (cũng hay được gọi là bán lẻ) , RiskType_lv2 = RRTD bán lẻ
        -	QLRRTH: tên phòng Quản lý rủi ro tích hợp
        -	Về phân khúc các sản phẩm:
        o	Re đại diện cho vay bất động sản
        o	IBIZ đại diện cho vay sản xuất kinh doanh (SXKD)
        o	CONS hoặc CSE: cho vay tiêu dùng có TSBĐ
        o	UNSEC hoặc CUS cho vay tiêu dùng không có TSBĐ
        o	CAR: cho vay mua ô tô, xe máy tiêu dùng
        o	CC: thẻ tín dụng
        o	OTH: cho vay khác

"""



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