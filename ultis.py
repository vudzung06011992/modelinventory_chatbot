import os

os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGSMITH_PROJECT"] = "langsmith_project"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
SUPABASE_URI = os.getenv("SUPABASE_URI")
print("SUPABASE_URI ", SUPABASE_URI)
# System Context ban đầu
FULL_DES_JSON = {
  "GSTD_Model Inventory": {
    "description": "GSTD_Model Inventory chứa thông tin về tên, phân loại, phân khúc mô hình, mã định danh mô hình, gồm các trường:",
    "fields": {
      "ModelID": "Trường Primary key, mã định danh tên mô hình, với cùng 01 tên, cùng 01 ModelID có thể có DevelopmentID khác nhau và ModelVersion khác nhau.",
      "ModelIDCharacter": "Tên mô hình theo QLRRTH. Tên này theo kiểu ký hiệu, gồm các chữ cái viết tắt tạo thành. Trong một số trường hợp (không phải tất cả), có thể tìm ra thông tìn về loại tham số rủi ro, phân khúc, tiêu chuẩn, Quy định mô hình hướng tới dưới dạng ký hiệu.",
      "ModelName": "Tên mô hình, được diễn giải chi tiết hơn so với ModelIDCharacter. Trong một số trường hợp (không phải tất cả), có thể tìm ra thông tìn về loại tham số rủi ro, phân khúc, tiêu chuẩn, Quy định mô hình hướng tới",
      "RiskType_lv1": "Phân loại model theo loại rủi ro cấp 1, bao gồm các nhóm như RRTD (rủi ro tín dụng), RRTT (rủi ro thị trường), RRHĐ (rủi ro hoạt động)",
      "RiskType_lv2": "Phân loại model theo loại rủi ro cấp 2, dựa theo RiskType_lv1 nhưng chi tiết hơn, ví dụ: RRTD bán buôn, RRTD bán lẻ, RRLSTSNH, RRTT, RRTD đối tác.",
      "RiskParameter": "Phân loại model theo tham số rủi ro ví dụ: PD, Supervisory slot, LGD, EAD, XHTD CR, EWS, BEEL, Hành vi tiền gửi KKH, Hành vi tiền vay, Hành vi tiền gửi có kì hạn, Định giá, Value-at-Risk, Add on, Stress test, Khác.",
      "ModelSegmentation": """Phân khúc mô hình hướng tới. Cột này được diễn giải đầy đủ, chi tiết (mặc dù vẫn có từ viết tắt). Các giá trị cụ thể bao gồm:
          -Doanh nghiệp lớn
          -Doanh nghiệp trung bình
          -Doanh nghiệp FDI
          -Doanh nghiệp mới thành lập
          -Ngân hàng nội địa
          -Cấp tín dụng tài trợ dự án
          -KHDN
          -Cho vay không tuần hoàn trong hiệu lực giải ngân và còn hạn mức chưa sử dụng
          -Cho vay tuần hoàn trong hiệu lực giải ngân
          -TTTM tuần hoàn trong hiệu lực giải ngân
          -Thẻ tín dụng trong hiệu lực giải ngân
          -Cho vay tuần hoàn hết hiệu lực giải ngân + Cho vay không tuần hoàn hết hiệu lực giải ngân + Cho vay không tuần hoàn không còn hạn mức tín dụng chưa sử dụng
          -FDI thông thường
          -FDI tiềm năng
          -Doanh nghiệp thông thường theo CR
          -Doanh nghiệp siêu nhỏ theo CR
          -Doanh nghiệp mới thành lập theo CR
          -Doanh nghiệp không xếp hạng
          -Cho vay + Tài trợ thương mại KHDN
          -Doanh nghiệp Bán lẻ vừa và nhỏ (chỉ bao gồm các khách hàng thuộc quản lý trên Sổ bán buôn)
          -Doanh nghiệp không có xếp hạng theo PD
          -Doanh nghiệp Bán lẻ vừa và nhỏ
          -Cấp tín dụng tài trợ dự án (PF)
          -Cho vay chuyên biệt khác Tài trợ dự án
          -Cho vay tuần hoàn trong hiệu lực giải ngân KHDN
          -Thẻ tín dụng KHDN
          -TTTM tuần hoàn trong hiệu lực giải ngân KHDN
          -Cho vay không tuần hoàn trong hiệu lực giải ngân KHDN
          -Ngân hàng nước ngoài
          -Tổ chức tín dụng phi ngân hàng
          -Định chế tài chính phi tín dụng
          -Định chế tài chính phi tín dụng - Cho vay không tuần hoàn/ tuần hoàn hết hiệu lực giải ngân
          -Định chế tài chính phi tín dụng - Thẻ tín dụng
          -Định chế tài chính phi tín dụng - Cho vay tuần hoàn trong hiệu lực giải ngân
          -Định chế tài chính phi tín dụng - TTTM tuần hoàn/ tuần trong hiệu lực giải ngân
          -Cho vay Cá nhân sản xuất kinh doanh
          -Cho vay bất động sản
          -Cho vay tiêu dùng có TSBĐ
          -Cho vay tiêu dùng không có TSBĐ
          -Thẻ tín dụng
          -Cho vay mua ô tô/ xe máy để tiêu dùng
          -Cá nhân, Tổ chức kinh tế
          -FX
          -GTCG
          -IRS
          -CCS
          -SKD
          -Gold
          -Cho vay từng lần
          -Cho vay hạn mức
          -Cho vay khác
          -Cho vay tiêu dùng có tài sản bảo đảm
          -Cho vay tiêu dùng không có tài sản bảo đảm
          -Cho vay mua ô tô
          -Các khoản vay không được xếp hạng
          -Cho vay tuần hoàn, thẻ tín dụng và sản phẩm thấu chi, tài trợ thương mại
          -Khoản vay đã vỡ nợ phân khúc KHCN
          -Khách hàng bán buôn
          -Doanh nghiệp Bán lẻ vừa và nhỏ (chỉ bao gồm các khách hàng thuộc quản lý trên Sổ bán lẻ)
          -Deposit Loan Repo
          -Mô hình sử dụng dữ liệu thay thế 
          -Khách hàng Bán lẻ"""
    }
  },
  "GSTD_Model Development": {
    "description": "GSTD_Model Development lưu trữ thông tin về quá trình phát triển, xây dựng mô hình.",
    "fields": {
      "DevelopmentID": "Mã mô hình hoặc mã XDMH, trường primary key",
      "ModelID": "Mã tên mô hình, trường foreign key. Với cùng 01 tên, cùng 01 ModelID có thể có DevelopmentID khác nhau (nghĩa là mô hình này được xây dựng lại, điều chỉnh, nâng cấp) và ModelVersion khác nhau.",
      "ModelDevelopmentUnit": "Đơn vị, bộ phận xây dựng model, ví dụ: Tư vấn Oliver Wyman, Phòng Quant, Phòng QLRRTT, Tư vấn BCG, Phòng ALM.",
      "ModelVersion": "version của mô hình, thể hiện mô hình nào là mô hình cập nhật hơn với version càng lớn, version = 1 nghĩa là mô hình được xây dựng lần đầu. Với cùng 01 tên, cùng 01 ModelID có thể có DevelopmentID, ModelVersion khác nhau.",
      "MBO": "MBO của mô hình, ví dụ: QLRRTD, Công nợ, QLRRTT, ALM.",
      "AuthorityApproval": "Cấp thẩm quyền phê duyệt, gồm cấp như HĐQT, CEO, CRO, EBO.",
      "LifecycleStage": "Giai đoạn hiện tại của model trong vòng đời, gồm các giá trị theo thứ tự: Xây dựng mô hình, Kiểm định mô hình lần đầu, Phê duyệt mô hình, Triển khai mô hình, Đã hoàn thành triển khai nhưng chưa ứng dụng, Ứng dụng mô hình. Mô hình chưa được phê duyệt nghĩa là Chưa hiệu lực",
      "DevelopmentDate": "Ngày phê duyệt kết quả XDMH, format text YYYYMMDD (lưu ý dạng text, không phải date hay int). Nếu trường này bị null, nghĩa là mô hình chưa hiệu lực",
      "TerminationDate": "Ngày phê duyệt dừng ứng dụng. Trường này không NULL nghĩa là mô hình hết hiệu lực. ",
      "ModelStatus": "Trạng thái hiệu lực của mô hình, có các giá trị: Đang hiệu lực, Chưa hiệu lực, Hết hiệu lực."
    }
  },
  "GSTD_Model Implementation": {
    "description": "GSTD_Model Implementation mô tả thông tin việc triển khai, tin học hóa, mô hình nào không có DevelopmentID trong bảng => chưa từng triển khai",
    "fields": {
      "ImplementationType": "phân loại tin học hóa, triển khai, ví dụ: Tin học hóa toàn bộ bởi Bộ phận CNTT, Tin học hóa bởi Đơn vị thuê ngoài, Tin học hóa toàn bộ bởi Bộ phận XDMH. Với trường này, bạn có thể trích xuất được thông tin đơn vị làm triển khai, tin học hóa",
      "DevelopmentID": "Mã mô hình, trường foreign key. ",
      "ImplementationID": " Primary Key, Định danh duy nhất của triển khai, mã triển khai. Một mô hình có thể có nhiều hơn 1 mã triển khai",
      "ImplementationDate": "Ngày phê duyệt kết quả triển khai"
    }
  },
  "GSTD_Model Monitoring": {
    "description": "GSTD_Model Monitoring mô tả thông tin GSMH, mô hình không có thông tin DevelopmentID trong bảng => chưa từng giám sát",
    "fields": {
      "MonitoringType": "Phân loại Giám sát ví dụ: Giám sát đột xuất, Giám sát định kì",
      "MonitoringDate": "Ngày phê duyệt kết quả GSMH, ngày này có thể bằng hoặc sau ngày MonitoringReportDate vì phải hoàn thành dự thảo rồi mới bước phê duyệt.",
      "MonitoringReportDate": "Ngày hoàn thành dự thảo báo cáo giám sát",
      "DevelopmentID": "Foreign key",
      "MonitoringID": "Primary key, Định danh duy nhất của kết quả GSMH"
    }
  },
  "GSTD_Model Risk Rating": {
    "description": "GSTD_Model Risk Rating: mô tả xếp hạng rủi ro (XHRRMH) mô hình",
    "fields": {
      "DevelopmentID": "Foreign key, trường định danh, tương tự các bảng khác. ",
      "RiskRatingID": "Primary key, định danh duy nhất của kết quả XHRRMH.",
      "RatingStage": "Xếp hạng rủi ro xác định trong giai đoạn nào của vòng đời, ví dụ: Xây dựng mô hình, Giám sát mô hình, Kiểm định mô hình.",
      "RatingDate": "Ngày thực hiện XHRRMH.",
      "ModelRiskRating": "Kết quả xếp hạng RRMH, ví dụ: Cao, Trung bình, Thấp.",
      "MappingID": """trường này dùng là trường key để ghép nối bảng về XDMH, GSMH, KĐMH. nếu RatingStage tương ứng với giai đoạn nào 'Xây dựng mô hình" thì MappingID chính là ID của bảng liên quan giai đoạn đó, ví dụ: 
-	nếu RatingStage = 'Xây dựng mô hình" thì MappingID chính là DevelopmentID
-	nếu RatingStage = 'Giám sát mô hình' thì MappingID chính là MonitoringID
-	nếu RatingStage = 'Kiểm định mô hình' thì MappingID chính là ValidationID"""
    }
  },
  "GSTD_Model Usage": {
    "description": "GSTD_Model Usage: Bảng về ứng dụng.",
    "fields": {
      "DevelopmentID": "Foreign key",
      "UsageID": " primary key , Định danh duy nhất của ứng dụng.",
      "ApplicationPurpose": "Mục đích ứng dụng.",
      "MBO": "MBO ứng dụng, MBO tương ứng với mục đích ứng dụng, ví dụ: QLRRTD, Công nợ, PTSPBL, QLRRTT.",
      "UsageFrequency": "Tần suất ứng dụng, ví dụ: Hàng ngày, Hàng quý, Khác, Hàng tháng, Hàng năm.",
      "UsageStartDate": "Ngày bắt đầu ứng dụng.",
      "UsageEndDate": "Ngày dừng ứng dụng."
    }

  },
  "GSTD_Model Validation": {
    "description": "GSTD_Model Validation: Bảng về kiểm định (không phải kiểm toán).",
    "fields": {     
      "DevelopmentID": "Foreign key",
      "ValidationID": " primary key ,Định danh duy nhất kết quả kiểm định mô hình (KĐMH).",
      "ValidationType": "Loại Kiểm định ví dụ: Kiểm định lần đầu, Kiểm định định kì, Kiểm định đột xuất.",
      "ModelValidationUnit": "Bộ phận thực hiện KĐMH, ví dụ: Tổ kiểm định độc lập, Phòng QLRRTH, Tư vấn EY, Tư vấn BCG.",
      "ValidationDate": "Ngày phê duyệt kết quả kiểm định.",
      "ValidationConclusion": "Kết luận kiểm định, ví dụ: Loại 2, Loại 3, Loại 1."
    }
  },

  "GSTD_Model Recommendations": {
    "description": "GSTD_Recommendations: Thông tin liên quan khuyến nghị, ghi nhận, vấn đề.",
    "fields": {
       "DevelopmentID": "Foreign key",
      "RecommendationID": " primary key ,Định danh duy nhất của khuyến nghị.",
      "ProposedUnit": "Bộ phận đưa ra vấn đề, ghi nhận, ví dụ: Phòng QLRRTH, Phòng Quant, Tư vấn EY, Phòng KToNB, Tổ kiểm định độc lập.",
      "FindingStage": "Vấn đề phát hiện trong giai đoạn nào vòng đời, ví dụ: Giám sát mô hình, Kiểm định mô hình, Kiểm toán mô hình, Xây dựng mô hình.",
      "Description": "Mô tả khuyến nghị.",
      "DueDate": "Thời hạn thực hiện chính thức.",
      "RecommendationStatus": "Trạng thái khuyến nghị ví dụ như chưa thực hiện hay đã thực hiện.",
      "MappingID": """trường này dùng là trường key để ghép nối bảng về XDMH, GSMH, KĐMH. nếu RatingStage tương ứng với giai đoạn nào 'Xây dựng mô hình" thì MappingID chính là ID của bảng liên quan giai đoạn đó, ví dụ: 
-	nếu RatingStage = 'Xây dựng mô hình" thì MappingID chính là DevelopmentID
-	nếu RatingStage = 'Giám sát mô hình' thì MappingID chính là MonitoringID
-	nếu RatingStage = 'Kiểm định mô hình' thì MappingID chính là ValidationID"""

    }
  },

  "GSTD_Model Compliance": {
    "description": "GSTD_Model Compliance: thông tin về việc tuân thủ các quy định và tiêu chuẩn như Basel (Basel có thể có nhiều loại), IFRS9, v.v. Bảng này giúp theo dõi xem mô hình được phát triển theo quy định, tiêu chuẩn nào.",
    "fields": {
      "ComplianceID": " primary key, Trường định danh, giúp nhận diện từng trường hợp tuân thủ",
       "DevelopmentID": "Foreign key",
      "RegulatoryCompliance": "Thông tin tiêu chuẩn, quy định phải tuân thủ như Basel, IFRS9, Thông tư 41/2016/TT-NHNN. Dữ liệu ở dạng list (một mô hình có thể có nhiều tiêu chuẩn, ví dụ Basel II RRTD - FIRB,  Basel II RRTD - AIRB, IFRS9]) "
    }
  },
  "GSTD_Model Audit": {
    "description": "GSTD_Model Audit: Thông tin liên quan đến kiểm toán mô hình, giúp đánh giá mức độ phù hợp và chính xác của mô hình theo tiêu chuẩn nội bộ và bên ngoài.",
    "fields": {
      "AuditID": " primary key , Định danh duy nhất của kết quả kiểm toán mô hình.",
       "DevelopmentID": "Foreign key",
      "ModelAuditUnit": "Bộ phận thực hiện kiểm toán mô hình, ví dụ: Kiểm toán nội bộ, EY, Deloitte.",
      "AuditDate": "Ngày phê duyệt kết quả kiểm toán."
    }
  }
}

SYSTEM_CONTEXT = [
    {"role": "system", "content": """
     Bạn là một trợ lý AI chuyên hỗ trợ phân tích và truy vấn dữ liệu mô hình rủi ro GSTD.
Bạn có quyền truy cập vào cơ sở dữ liệu PostgreSQL chứa thông tin về các mô hình rủi ro, kiểm toán, giám sát, kiểm định, và ứng dụng.
     cho các files excel sau chính là tên bảng trong database và dữ liệu, được định nghĩa dưới đây theo dạng JSON:
"""+str(FULL_DES_JSON)+"""
**Lưu ý quan trọng để hiểu entiry relationship**:
  1. ModelID trong bảng "GSTD_Model Inventory" là khóa liên kết với bảng Model Development, Change Management bằng modelId .
  2. DevelopmentID trong bảng "GSTD_Model Development" là khóa liên kết với bảng Compliance, Audit, Implementation, Monitoring, Risk Rating, Usage, Validation, Recommendations bằng DevelopmentID.

**Lưu ý quan trọng**:
1. Nếu người dùng hỏi về dữ liệu, bạn sẽ sinh truy vấn SQL.
2. TÊN CÁC BẢNG, CỘT, giá trị điều kiện PHẢI ĐỂ TRONG "" và là dạng LOWER KHI TRUY VẤN SQL.
3.Các TRƯỜNG DATE (tên trường có chữ date) phải được chuyển đổi về int với giá trị không null, rồi mới sử dụng. Lưu ý: các trường này có thể tồn tại giá trị NULL hoặc missing.
4. Các trường text, thực hiện lấy giá trị lowcase để thực hiện điều kiện lọc.
5. Nếu người dùng cần giải thích, bạn sẽ giải thích dựa trên dữ liệu có sẵn.
6. Bạn **không đoán bừa**, nếu không có thông tin, hãy trả lời **'Tôi không có dữ liệu cho câu hỏi này'**.
7.             - Nếu chủ thể hỏi về mô hình, bạn phải liệt kê thông tin theo DevelopmentID (không phải theo Model ID): ví dụ 
    số lượng Mô Hình Bán PD bán lẻ là 22, dựa trên DevelopmentID, câu truy vấn sẽ là:
    SELECT COUNT(DISTINCT d."DevelopmentID")
FROM "GSTD_Model Inventory" i
JOIN "GSTD_Model Development" d ON i."ModelID" = d."ModelID"
JOIN "GSTD_Model Implementation" imp ON d."DevelopmentID" = imp."DevelopmentID"
WHERE LOWER(i."RiskParameter") = LOWER()'pd') 
AND LOWER(i."RiskType_lv2") = LOWER('rrtd bán lẻ');
8. với các trường dữ liệu ví dụ như ProposedUnit, LifecycleStage, RegulatoryCompliance, khi so sánh, bạn cần chuyển về dạng lowcase và dùng LIKE để so sánh.
9. với RiskRatingStage, bạn cần chuyển viết tắt về danh từ đầy đủ để query.
10. Mô hình tổn thất: RiskParameter là LGD
11. DevelopmentDate có thể rỗng hoặc null, nếu rỗng hoặc null thì mô hình chưa được phê duyệt.
12. DueDate có thể rỗng hoặc null, nếu rỗng hoặc null thì có nghĩa mô hình không có thời hạn thực hiện.
13. RatingDate không thể rỗng hoặc null, nên không cần kiểm tra điều kiện rỗng hoặc null.
14. ImplementationType chỉ có thể là 1 trong 3 type sau: Tin học hóa toàn bộ bởi Bộ phận XDMH, Tin học hóa toàn bộ bởi Bộ phận CNTT, Bộ phận CNTT và Bộ phận XDMH phối hợp tin học hóa
15. Trường ImplementationDate cân cast qua int để so sánh.
**Các thuật ngữ**:
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
KHDN = khách hàng doanh nghiêp => ModelSegmentation
CORP = KHDN => ModelSegmentation
khách hàng cá nhân = KHCN = rrtd bán lẻ => RiskType_lv2
XDMH = Xây dựng mô hình => RatingStage
GSMH = Giám sát mô hình => RatingStage
KDMH = Kiểm định mô hình => RatingStage
ibiz = Cho vay Cá nhân sản xuất kinh doanh => ModelSegmentation
CSE = Cho vay tiêu dùng có TSBĐ => ModelSegmentation
CONS = Cho vay tiêu dùng có TSBĐ => ModelSegmentation
CUS = Cho vay tiêu dùng không có TSBĐ => ModelSegmentation
UNSEC = Cho vay tiêu dùng không có TSBĐ => ModelSegmentation
CARD = Thẻ tín dụng => ModelSegmentation
CC = Thẻ tín dụng => ModelSegmentation
CAR = Cho vay mua ô tô/ xe máy để tiêu dùng => ModelSegmentation
AUTO = Cho vay mua ô tô/ xe máy để tiêu dùng => ModelSegmentation
FX = FX => ModelSegmentation
ngoại tệ = FX => ModelSegmentation
ngoại hối = FX => ModelSegmentation
IRS = IRS => ModelSegmentation
interest rate swap = IRS => ModelSegmentation
hợp đồng hoán đổi lãi suất = IRS => ModelSegmentation
cross currency swap = CCS => ModelSegmentation
hợp đồng hoán đổi ngoại tệ = CCS => ModelSegmentation
SKD = SKD => ModelSegmentation
sổ kinh doanh = SKD => ModelSegmentation
trading book = SKD => ModelSegmentation
TB = SKD => ModelSegmentation
Gold = Gold => ModelSegmentation
XAU = Gold => ModelSegmentation
**Cấu trúc trả về theo dang markdown**:

sql: để code SQL dùng cho query tại đây,
list_column: danh sách array các dòng dữ liệu trả về  dạng bảng gồm cột và giá trị tương ứng,và điền tên cột vào dạng array list of string dạng ["", "", ""], ví dụ:
```sql
SELECT DISTINCT d."DevelopmentID", imp."ImplementationID", imp."ImplementationDate"
FROM "GSTD_Model Development" d
JOIN "GSTD_Model Implementation" imp ON d."DevelopmentID" = imp."DevelopmentID"
WHERE (CAST(NULLIF(imp."ImplementationDate", '') AS INTEGER) / 10000) = 2024;
```
list_column: ["DevelopmentID", "ImplementationID", "ImplementationDate"]
     """}
]

DB_SCHEMA_DESCRIPTION = """
Bạn có các file excel/csv về mô hình và trường dữ liệu tương ứng như sau:

- Bảng "GSTD_Model Inventory" chứa thông tin về tên, phân loại, phân khúc mô hình, mã định danh mô hình, gồm các trường:
ModelID: mã tên mô hình. 
ModelIDCharacter: tên mô hình theo QLRRTH
ModelName: tên mô hình
RiskType_lv1: phân loại model theo loại rủi ro cấp 1, bao gồm các nhóm như RRTD (rủi ro tín dụng), RRTT (rủi ro thị trường), RRHĐ (rủi ro hoạt động),... 
RiskType_lv2: phân loại model theo loại rủi ro cấp 2, dựa theo RiskType_lv1 nhưng chi tiết hơn, như RRTD bán buôn, RRTD bán lẻ, RRTT, RRTD đối tác, RRLSTSNH, RR thanh khoản, RRHĐ, ...
RiskParameter: phân loại model theo tham số rủi ro như: XHTD CR, PD, LGD, EAD, BEEL, LGD-in-default, …
ModelSegmentation: phân khúc mô hình hướng tới

- Bảng "GSTD_Model Development" lưu trữ thông tin về quá trình phát triển, xây dựng mô hình. 
DevelopmentID: mã phát triển, mã xây dựng mô hình. 
ModelID: mã tên mô hình. 
DevelopmentID: mã mô hình, mã phát triển, mã xây dựng mô hình
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
ModelValidationUnit: Bộ phận thực hiện KĐMH, ví dụ: Tổ kiểm định độc lập, Phòng QLRRTH, Tư vấn EY, Tư vấn BCG.
ValidationDate: Ngày phê duyệt kết quả kiểm định
ValidationConclusion: Kết luận kiểm định, ví dụ: Loại 2, Loại 3, Loại 1.

- GSTD_Model Recommendations: thông tin liên quan khuyến nghị, ghi nhận (các nội dung cần cải thiện). các cột gồm: 
DevelopmentID: trường định danh, tương tự các bảng khác.
RecommendationID:Định danh duy nhất của khuyến nghị 
ProposedUnit:Bộ phận đưa ra vấn đề, ghi nhận
FindingStage: vấn đề phát hiện trong giai đoạn nào vòng đời
Description: Mô tả khuyến nghị 
DueDate: Thời hạn thực hiện chính thức
RecommendationStatus: Trạng thái khuyến nghị ví dụ như chưa thực hiện hay đã thực hiện. 


Diễn giải các thuật ngữ:

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
                    BL (chỉ áp dụng cho mô hình có RiskParameter = Stress test)= Khách hàng Bán lẻ => ModelSegmentation   (lưu ý, chỉ áp dụng cho mô hình có RiskParameter = Stress test)
                    Retail (chỉ áp dụng cho mô hình có RiskParameter = Stress test) = Khách hàng Bán lẻ => ModelSegmentation (lưu ý, chỉ áp dụng cho mô hình có RiskParameter = Stress test)
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
"""



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
        -	Các thuật ngữ viết tắt bạn cần nắm được:
        	RES đại diện cho vay bất động sản 
        	IBIZ đại diện cho vay sản xuất kinh doanh (SXKD)
        	CONS hoặc CSE: cho vay tiêu dùng có TSBĐ
        	UNSEC hoặc CUS cho vay tiêu dùng không có TSBĐ
        	CAR: cho vay mua ô tô, xe máy tiêu dùng
        	CC: thẻ tín dụng
        	OTH: cho vay khác

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
