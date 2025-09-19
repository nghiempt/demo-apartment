import streamlit as st
import requests
import json
from datetime import datetime
import os

# Page configuration
st.set_page_config(
    page_title="Apartment Search Chat",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .chat-message {
        padding: 1rem;
        border-radius: 0.8rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #e3f2fd;
        color: #0d47a1;
        border-left: 4px solid #2196f3;
    }
    .assistant-message {
        background-color: #f3e5f5;
        color: #4a148c;
        border-left: 4px solid #9c27b0;
    }
    .apartment-info {
        background-color: #f8f9fa;
        color: #212529;
        border: 1px solid #dee2e6;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .image-container {
        text-align: center;
        margin: 1rem 0;
    }
    .error-message {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# API configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

def call_chat_api(query):
    """Call the chat API endpoint"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/chat",
            headers={"Content-Type": "application/json"},
            json={"query": query},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Không thể kết nối đến API. Vui lòng kiểm tra server có đang chạy không."}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "API timeout. Vui lòng thử lại."}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Lỗi API: {str(e)}"}
    except json.JSONDecodeError:
        return {"success": False, "error": "Lỗi phản hồi từ API"}

def display_message(message, is_user=False):
    """Display a chat message"""
    message_class = "user-message" if is_user else "assistant-message"
    icon = "👤" if is_user else "🤖"
    
    st.markdown(f"""
    <div class="chat-message {message_class}">
        <div><strong>{icon} {"Bạn" if is_user else "Assistant"}</strong></div>
        <div style="margin-top: 0.5rem;">{message}</div>
    </div>
    """, unsafe_allow_html=True)

def display_apartment_info(apartment_info):
    """Display apartment information in a formatted way"""
    st.markdown("""
    <div class="apartment-info">
        <h4>📋 Thông tin chi tiết căn hộ</h4>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**🏷️ Mã căn:** {apartment_info.get('mã_căn', 'N/A')}")
        st.write(f"**🏢 Phân khu:** {apartment_info.get('phân_khu', 'N/A')}")
        st.write(f"**🏗️ Tầng:** {apartment_info.get('tầng', 'N/A')}")
        st.write(f"**🏠 Loại hình:** {apartment_info.get('loại_hình', 'N/A')}")
    
    with col2:
        st.write(f"**📏 Diện tích tim tường:** {apartment_info.get('diện_tích_tim_tường', 'N/A')} m²")
        st.write(f"**📐 Diện tích thông thủy:** {apartment_info.get('diện_tích_thông_thủy', 'N/A')} m²")
        st.write(f"**💰 Giá bán:** {apartment_info.get('giá_formatted', 'N/A')}")
        st.write(f"**📍 Căn góc:** {'✅ Có' if apartment_info.get('căn_góc') else '❌ Không'}")

def display_images(images_urls):
    """Display apartment images"""
    if images_urls:
        st.markdown("### 🖼️ Hình ảnh căn hộ")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if "blueprint" in images_urls:
                st.markdown("**📐 Bản vẽ kỹ thuật:**")
                st.image(images_urls["blueprint"], caption="Blueprint", use_column_width=True)
        
        with col2:
            if "map" in images_urls:
                st.markdown("**🗺️ Sơ đồ vị trí:**")
                st.image(images_urls["map"], caption="Map", use_column_width=True)

# Main UI
st.title("🏠 Apartment Search Chat")
st.markdown("Hỏi tôi về thông tin căn hộ, tôi sẽ giúp bạn tìm kiếm và cung cấp thông tin chi tiết!")

# Sidebar with example queries
with st.sidebar:
    st.header("💡 Ví dụ câu hỏi")
    example_queries = [
        "Cho tôi thông tin căn góc tầng 2 phân khu Origami",
        "Cho tôi thông tin chi tiết căn hộ số 08, tầng 2, phân khu Origami",
        "Căn hộ số 17, tầng 2, Origami hiện có loại hình và giá bao nhiêu?",
        "Thông tin đầy đủ của căn góc số 26, tầng 2, Origami là gì?"
    ]
    
    for query in example_queries:
        if st.button(query, key=f"example_{hash(query)}", use_container_width=True):
            st.session_state.example_query = query

# Display chat history
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        if message["type"] == "user":
            display_message(message["content"], is_user=True)
        elif message["type"] == "assistant":
            display_message(message["content"], is_user=False)
            
            # Display apartment info if available
            if "apartment_info" in message:
                display_apartment_info(message["apartment_info"])
            
            # Display images if available
            if "images_urls" in message:
                display_images(message["images_urls"])
                
            # Display total found
            if "total_found" in message:
                st.info(f"🔍 Tìm thấy tổng cộng {message['total_found']} căn hộ phù hợp")
        
        elif message["type"] == "error":
            st.markdown(f"""
            <div class="error-message">
                <strong>❌ Lỗi:</strong> {message["content"]}
            </div>
            """, unsafe_allow_html=True)

# Chat input
st.markdown("---")

# Handle example query from sidebar
if "example_query" in st.session_state:
    user_input = st.session_state.example_query
    del st.session_state.example_query
else:
    user_input = st.chat_input("Nhập câu hỏi của bạn về căn hộ...")

if user_input:
    # Add user message to chat history
    st.session_state.messages.append({
        "type": "user",
        "content": user_input,
        "timestamp": datetime.now()
    })
    
    # Show loading spinner
    with st.spinner("Đang tìm kiếm thông tin căn hộ..."):
        # Call API
        response = call_chat_api(user_input)
    
    if response.get("success"):
        # Add assistant response to chat history
        assistant_message = {
            "type": "assistant",
            "content": response.get("message", ""),
            "timestamp": datetime.now()
        }
        
        # Add additional data if available
        if "apartment_info" in response:
            assistant_message["apartment_info"] = response["apartment_info"]
        
        if "images_urls" in response:
            assistant_message["images_urls"] = response["images_urls"]
            
        if "total_found" in response:
            assistant_message["total_found"] = response["total_found"]
        
        st.session_state.messages.append(assistant_message)
    else:
        # Add error message
        st.session_state.messages.append({
            "type": "error",
            "content": response.get("error", "Có lỗi xảy ra khi xử lý yêu cầu"),
            "timestamp": datetime.now()
        })
    
    # Rerun to display new messages
    st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.8rem;">
    💡 Tip: Hãy hỏi cụ thể về phân khu, tầng, loại căn hộ để được tư vấn tốt nhất!
</div>
""", unsafe_allow_html=True)

# Clear chat button in sidebar
with st.sidebar:
    st.markdown("---")
    if st.button("🗑️ Xóa lịch sử chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    # API status check
    st.markdown("### 🔌 Trạng thái API")
    try:
        health_check = requests.get(f"{API_BASE_URL}/", timeout=5)
        if health_check.status_code == 200:
            st.success("✅ API đang hoạt động")
        else:
            st.error("❌ API có vấn đề")
    except:
        st.error("❌ Không thể kết nối API")