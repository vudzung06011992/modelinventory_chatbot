import re
import time

import pandas as pd
import chainlit as cl
import openai
from ultis import *
from langchain.sql_database import SQLDatabase
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool

db = SQLDatabase.from_uri(SUPABASE_URI)
execute_query_tool = QuerySQLDatabaseTool(db=db)

decode_table = pd.read_excel("BANGMAHOA.xlsx", engine='openpyxl' )
@cl.on_message
async def chat_with_gpt(message: cl.Message):
    start_time = time.time()
    # Kiểm tra nếu đã có lịch sử chat trước đó, nếu không thì tạo mới
    if not cl.user_session.get("conversation_history"):
        cl.user_session.set("conversation_history", SYSTEM_CONTEXT.copy())
    print(SYSTEM_CONTEXT)
    # Lấy lịch sử hội thoại hiện tại
    conversation_history = cl.user_session.get("conversation_history")

    # Thêm tin nhắn người dùng vào hội thoại
    user_message = decode_keyword_func(message.content, decode_table)
    conversation_history.append({"role": "user", "content": user_message})

    # Gọi API OpenAI để lấy phản hồi
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=conversation_history
    )

    # Lấy nội dung phản hồi
    assistant_reply = response.choices[0].message.content
    print("assistant_reply: ", assistant_reply)
    # Thêm phản hồi vào lịch sử hội thoại
    conversation_history.append({"role": "assistant", "content": assistant_reply})

    # Lưu lại hội thoại vào session để duy trì context
    cl.user_session.set("conversation_history", conversation_history)
    sql_code = extract_sql_query(assistant_reply)
    list_column = get_column_name_from_response(assistant_reply)
    if sql_code:
        try:
            print("Running SQL Query:", sql_code)
            result = execute_query_tool.run(sql_code)
            data = eval(str(result))
            df = pd.DataFrame(data, columns=list_column)
            print("len df: ", len(df))
            markdown_table = df.to_markdown(index=False)
            # Sửa lỗi TypeError: chỉ truyền 1 tham số
            response_time = time.time() - start_time
            print("response_time: ", response_time)
            await cl.Message(content=f"**Thời gian phản hồi**:{response_time} giây \n**kết quả truy vấn:**\n \n{markdown_table}\n \n**Câu lệnh SQL:**\n```sql\n{sql_code}\n``` ").send()
        except Exception as e:
            await cl.Message({e}).send()
    else:
        await cl.Message(assistant_reply).send()



# Hàm nhận diện đoạn code SQL từ assistant_reply
def extract_sql_query(text):
    sql_pattern = r"```sql\n(.*?)\n```"
    match = re.search(sql_pattern, text, re.DOTALL)
    return match.group(1) if match else None
    # Gửi phản hồi về UI Chainlit

def decode_keyword_func(text: str, code_mapping: pd.DataFrame) -> str:
    def replace_match(match):
        extracted_text = match.group(1).lower()
        
        # Chuyển CODE và VALUE về lowercase để so sánh
        code_mapping_lower = code_mapping.copy()
        code_mapping_lower['CODE'] = code_mapping_lower['CODE'].str.lower()
        code_mapping_lower['VALUE'] = code_mapping_lower['VALUE'].str.lower()
        
        # Tìm tất cả các bản ghi có CODE hoặc VALUE khớp với extracted_text
        records = code_mapping_lower[(code_mapping_lower['CODE'] == extracted_text) | (code_mapping_lower['VALUE'] == extracted_text)]
        if not records.empty:
            for _, record in records.iterrows():
                if record['COLUMN'] == "ModelSegmentation":
                    return f"có ModelSegmentation là {record['VALUE']}"
                elif record['COLUMN'] == "ModelName":
                    return f"có ModelName là {record['VALUE']}"
        
        # Nếu không map được, trả về chuỗi gốc không có dấu '
        return match.group(1)
    
    # Tìm tất cả các chuỗi trong dấu nháy đơn và thay thế từng cái
    processed_text = re.sub(r"'([^']+)'", replace_match, text)
    return processed_text
def get_column_name_from_response(openai_respose):
    match = re.search(r'list_column:\s*(\[[^\]]*\])', openai_respose)
    if match:
    # Tách phần danh sách và chuyển thành list
        list_column = eval(match.group(1))  # hoặc sử dụng ast.literal_eval(match.group(1)) để an toàn hơn
        return list_column
    else:
        return [0]
