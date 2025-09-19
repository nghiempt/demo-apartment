#!/usr/bin/env python3
"""
Apartment Search API - FastAPI server
Tìm kiếm căn hộ và trả về ảnh đã zoom + đánh dấu vị trí
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
import pandas as pd
import cv2
import numpy as np
import io
import base64
from typing import Dict, Tuple, Optional, List
import os
import requests
import tempfile
import openai
import json
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Apartment Search API",
    description="API để tìm kiếm căn hộ và trả về ảnh đã zoom với marker đỏ",
    version="1.0.0"
)

class ApartmentSearcher:
    def __init__(self):
        self.blueprint_data = None
        self.map_data = None
        self.sheet_data = None
        self.blueprint_image = None
        self.map_image = None
        self.load_data()
    
    def load_data(self):
        """Load CSV data và images"""
        try:
            # Get current directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Load CSV data
            self.blueprint_data = pd.read_csv(os.path.join(current_dir, "data", "blueprint.csv"))
            self.map_data = pd.read_csv(os.path.join(current_dir, "data", "map.csv"))
            self.sheet_data = pd.read_csv(os.path.join(current_dir, "data", "sheet.csv"))
            
            # Load images
            self.blueprint_image = cv2.imread(os.path.join(current_dir, "images", "blueprint.jpg"))
            self.map_image = cv2.imread(os.path.join(current_dir, "images", "map.jpg"))
            
            if self.blueprint_image is None:
                raise FileNotFoundError("blueprint.jpg not found")
            if self.map_image is None:
                raise FileNotFoundError("map.jpg not found")
                
            print("✅ Đã load thành công:")
            print(f"   📊 Blueprint: {len(self.blueprint_data)} căn hộ")
            print(f"   📊 Map: {len(self.map_data)} căn hộ")
            print(f"   � Sheet: {len(self.sheet_data)} căn hộ")
            print(f"   �🖼️  Blueprint image: {self.blueprint_image.shape}")
            print(f"   🖼️  Map image: {self.map_image.shape}")
            
        except Exception as e:
            print(f"❌ Lỗi load data: {e}")
            raise
    
    def get_apartment_coords(self, apartment_id: str) -> Tuple[Optional[Tuple[int, int]], Optional[Tuple[int, int]]]:
        """Lấy tọa độ của căn hộ từ cả 2 file CSV"""
        # Tìm trong blueprint
        blueprint_row = self.blueprint_data[self.blueprint_data['Apartment'] == apartment_id]
        blueprint_coords = None
        if not blueprint_row.empty:
            blueprint_coords = (int(blueprint_row.iloc[0]['X']), int(blueprint_row.iloc[0]['Y']))
        
        # Tìm trong map
        map_row = self.map_data[self.map_data['Apartment'] == apartment_id]
        map_coords = None
        if not map_row.empty:
            map_coords = (int(map_row.iloc[0]['X']), int(map_row.iloc[0]['Y']))
        
        return blueprint_coords, map_coords
    
    def create_zoomed_image_with_marker(self, image: np.ndarray, coords: Tuple[int, int], 
                                       zoom_size: int = 400, marker_size: int = 30, image_type: str = "map") -> np.ndarray:
        """
        Tạo ảnh đã zoom vào vị trí căn hộ với marker hộp vuông đỏ
        
        Args:
            image: Ảnh gốc
            coords: Tọa độ (x, y) của căn hộ
            zoom_size: Kích thước vùng zoom (px)
            marker_size: Kích thước padding cho hộp vuông marker (px)
            image_type: Loại ảnh ("blueprint" hoặc "map") để điều chỉnh kích thước marker
        """
        x, y = coords
        h, w = image.shape[:2]
        
        # Điều chỉnh kích thước marker dựa trên loại ảnh
        actual_marker_size = 90 if image_type == "blueprint" else marker_size
        
        # Tính toán vùng crop
        half_size = zoom_size // 2
        
        # Đảm bảo không vượt quá biên ảnh
        x1 = max(0, x - half_size)
        y1 = max(0, y - half_size)
        x2 = min(w, x + half_size)
        y2 = min(h, y + half_size)
        
        # Crop ảnh
        cropped = image[y1:y2, x1:x2].copy()
        
        # Tính tọa độ marker trong ảnh đã crop
        marker_x = x - x1
        marker_y = y - y1
        
        # Vẽ hộp vuông marker đỏ với padding
        # Tính toán tọa độ hộp vuông
        box_x1 = marker_x - actual_marker_size
        box_y1 = marker_y - actual_marker_size
        box_x2 = marker_x + actual_marker_size
        box_y2 = marker_y + actual_marker_size
        
        # Đảm bảo hộp vuông không vượt quá biên ảnh đã crop
        box_x1 = max(0, box_x1)
        box_y1 = max(0, box_y1)
        box_x2 = min(cropped.shape[1], box_x2)
        box_y2 = min(cropped.shape[0], box_y2)
        
        # Vẽ hộp vuông đỏ với độ trong suốt
        overlay = cropped.copy()
        cv2.rectangle(overlay, (box_x1, box_y1), (box_x2, box_y2), (0, 0, 255), -1)
        # Blend với ảnh gốc để tạo hiệu ứng trong suốt
        cv2.addWeighted(overlay, 0.3, cropped, 0.7, 0, cropped)
        
        # Vẽ viền đỏ đậm cho hộp vuông
        cv2.rectangle(cropped, (box_x1, box_y1), (box_x2, box_y2), (0, 0, 255), 3)
        
        # Vẽ viền đen bên ngoài để làm nổi bật
        cv2.rectangle(cropped, (box_x1-2, box_y1-2), (box_x2+2, box_y2+2), (0, 0, 0), 2)
        
        return cropped
    
    def search_apartment(self, apartment_id: str, zoom_size: int = 400) -> Dict:
        """
        Tìm kiếm căn hộ và trả về ảnh đã zoom
        
        Args:
            apartment_id: ID căn hộ (VD: CH01, CH02)
            zoom_size: Kích thước vùng zoom
        """
        # Chuẩn hóa apartment_id
        apartment_id = apartment_id.upper().strip()
        
        # Lấy tọa độ
        blueprint_coords, map_coords = self.get_apartment_coords(apartment_id)
        
        if not blueprint_coords and not map_coords:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy căn hộ {apartment_id}")
        
        result = {
            "apartment_id": apartment_id,
            "found_in": [],
            "images": {}
        }
        
        # Xử lý blueprint
        if blueprint_coords:
            result["found_in"].append("blueprint")
            result["blueprint_coords"] = {"x": blueprint_coords[0], "y": blueprint_coords[1]}
            
            zoomed_blueprint = self.create_zoomed_image_with_marker(
                self.blueprint_image, blueprint_coords, zoom_size, image_type="blueprint"
            )
            result["images"]["blueprint"] = zoomed_blueprint
        
        # Xử lý map
        if map_coords:
            result["found_in"].append("map")
            result["map_coords"] = {"x": map_coords[0], "y": map_coords[1]}
            
            zoomed_map = self.create_zoomed_image_with_marker(
                self.map_image, map_coords, zoom_size, image_type="map"
            )
            result["images"]["map"] = zoomed_map
        
        return result

# Khởi tạo searcher
searcher = None

def get_searcher():
    """Lazy initialization của searcher"""
    global searcher
    if searcher is None:
        searcher = ApartmentSearcher()
    return searcher

@app.get("/")
async def root():
    """Trang chủ API"""
    return {
        "message": "🏢 Apartment Search API",
        "version": "1.0.0",
        "endpoints": {
            "/search": "Tìm kiếm căn hộ",
            "/apartments": "Danh sách tất cả căn hộ",
            "/docs": "Swagger documentation"
        }
    }

@app.get("/apartments")
async def get_all_apartments():
    """Lấy danh sách tất cả căn hộ có sẵn"""
    searcher = get_searcher()
    blueprint_apartments = set(searcher.blueprint_data['Apartment'].tolist())
    map_apartments = set(searcher.map_data['Apartment'].tolist())
    all_apartments = sorted(blueprint_apartments.union(map_apartments))
    
    return {
        "total": len(all_apartments),
        "apartments": all_apartments,
        "blueprint_only": sorted(blueprint_apartments - map_apartments),
        "map_only": sorted(map_apartments - blueprint_apartments),
        "both": sorted(blueprint_apartments.intersection(map_apartments))
    }

def image_to_base64(image: np.ndarray) -> str:
    """Chuyển đổi OpenCV image sang base64 string"""
    _, buffer = cv2.imencode('.jpg', image)
    img_base64 = base64.b64encode(buffer).decode('utf-8')
    return img_base64

def upload_to_cloudinary(image: np.ndarray, apartment_id: str, image_type: str, zoom_size: int) -> str:
    """
    Upload image lên Cloudinary và trả về URL
    
    Args:
        image: OpenCV image array
        apartment_id: ID căn hộ
        image_type: Loại ảnh (blueprint/map)
        zoom_size: Kích thước zoom để đảm bảo unique public_id
    
    Returns:
        str: URL của ảnh trên Cloudinary
    """
    try:
        # Encode image to bytes
        _, buffer = cv2.imencode('.jpg', image)
        image_bytes = buffer.tobytes()
        
        # Prepare form data equivalent to curl command
        files = {
            'file': ('apartment.jpg', image_bytes, 'image/jpeg')
        }
        
        data = {
            'upload_preset': 'portal',
            'folder': 'other',
            'public_id': f'apartment_{apartment_id}_{image_type}_zoom{zoom_size}'
        }
        
        # Upload to Cloudinary via HTTP POST
        response = requests.post(
            'https://api.cloudinary.com/v1_1/farmcode/image/upload',
            files=files,
            data=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('secure_url', result.get('url'))
        else:
            print(f"❌ Cloudinary upload failed: {response.status_code} - {response.text}")
            # Fallback to base64 if upload fails
            return f"data:image/jpeg;base64,{image_to_base64(image)}"
        
    except Exception as e:
        print(f"❌ Lỗi upload Cloudinary: {e}")
        # Fallback to base64 if Cloudinary fails
        return f"data:image/jpeg;base64,{image_to_base64(image)}"

@app.get("/search")
async def search_apartment(
    apartment: str = Query(..., description="ID căn hộ (VD: CH01, CH02)", examples=["CH01"]),
    zoom_size: int = Query(100, description="Kích thước vùng zoom (px)", ge=10, le=3000),
    format: str = Query("json", description="Định dạng trả về: json hoặc images")
):
    """
    🔍 Tìm kiếm căn hộ và trả về ảnh đã zoom với marker đỏ
    
    - **apartment**: ID căn hộ (CH01, CH02, ...)
    - **zoom_size**: Kích thước vùng zoom (10-300px)
    - **format**: 'json' trả về Cloudinary URLs, 'images' trả về raw images
    """
    try:
        searcher = get_searcher()
        result = searcher.search_apartment(apartment, zoom_size)
        
        if format == "images":
            # Trả về ảnh thô (binary)
            if "blueprint" in result["images"]:
                blueprint_img = result["images"]["blueprint"]
                _, buffer = cv2.imencode('.jpg', blueprint_img)
                return Response(content=buffer.tobytes(), media_type="image/jpeg")
        
        # Chuyển images sang Cloudinary URLs cho JSON response
        images_urls = {}
        for img_type, img_data in result["images"].items():
            cloudinary_url = upload_to_cloudinary(img_data, apartment, img_type, zoom_size)
            images_urls[img_type] = cloudinary_url
        
        return {
            "success": True,
            "data": {
                "apartment_id": result["apartment_id"],
                "found_in": result["found_in"],
                "coordinates": {
                    k: v for k, v in result.items() 
                    if k.endswith("_coords")
                },
                "zoom_size": zoom_size,
                "images_urls": images_urls
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

# OpenAI Configuration
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY environment variable is required")
client = openai.OpenAI(api_key=openai.api_key)

class ChatAgent:
    def __init__(self, searcher: ApartmentSearcher):
        self.searcher = searcher
        
    def filter_apartments_by_query(self, query: str) -> List[Dict]:
        """
        Phân tích query và lọc căn hộ phù hợp từ sheet.csv
        """
        query_lower = query.lower()
        
        # Tạo bộ lọc dựa trên query
        filters = {}
        
        # Lọc theo phân khu
        if "origami" in query_lower:
            filters["PHÂN KHU"] = "Origami"
        
        # Lọc theo tầng
        floor_match = re.search(r"tầng\s*(\d+)", query_lower)
        if floor_match:
            filters["Tầng"] = int(floor_match.group(1))
        
        # Lọc theo căn góc
        if "căn góc" in query_lower or "can goc" in query_lower:
            filters["căn góc"] = True
        
        # Lọc theo số căn cụ thể
        # Patterns để tìm số căn: "căn số 08", "căn hộ số 08", "số 08", "căn 08"
        apartment_number_patterns = [
            r"căn\s*(?:số|hộ)?\s*(\d+)",
            r"số\s*(\d+)",
            r"căn\s*(\d+)"
        ]
        
        apartment_number = None
        for pattern in apartment_number_patterns:
            match = re.search(pattern, query_lower)
            if match:
                apartment_number = int(match.group(1))
                break
        
        # Áp dụng bộ lọc
        filtered_data = self.searcher.sheet_data.copy()
        
        for column, value in filters.items():
            if column in filtered_data.columns:
                filtered_data = filtered_data[filtered_data[column] == value]
        
        # Lọc theo số căn nếu có
        if apartment_number is not None:
            filtered_data = filtered_data[filtered_data["Căn STT"] == apartment_number]
        
        # Chuyển đổi sang dạng list of dict để dễ xử lý
        return filtered_data.to_dict('records')
    
    def apartment_id_to_ch_format(self, apartment_stt: int) -> str:
        """
        Chuyển đổi từ số căn STT sang format CHxx
        Ví dụ: 12 -> CH12, 1 -> CH01
        """
        return f"CH{apartment_stt:02d}"
    
    def format_price(self, price: float) -> str:
        """
        Format giá tiền thành dạng dễ đọc
        """
        if price >= 1000000000:  # Tỷ
            return f"{price/1000000000:.1f} tỷ VNĐ"
        elif price >= 1000000:  # Triệu
            return f"{price/1000000:.0f} triệu VNĐ"
        else:
            return f"{price:,.0f} VNĐ"
    
    async def process_query(self, user_query: str) -> Dict:
        """
        Xử lý query từ user và trả về kết quả kèm ảnh
        """
        try:
            # 1. Lọc căn hộ phù hợp
            filtered_apartments = self.filter_apartments_by_query(user_query)
            
            if not filtered_apartments:
                return {
                    "success": False,
                    "message": "Không tìm thấy căn hộ phù hợp với yêu cầu của bạn. Vui lòng kiểm tra lại thông tin như số căn, tầng, hoặc phân khu.",
                    "apartments": [],
                    "images": []
                }
            
            # 2. Chọn căn hộ phù hợp nhất (căn đầu tiên trong kết quả đã lọc)
            selected_apartment = filtered_apartments[0]
            apartment_ch_id = self.apartment_id_to_ch_format(selected_apartment["Căn STT"])
            
            # 3. Gọi API search để lấy ảnh
            search_result = self.searcher.search_apartment(apartment_ch_id, zoom_size=2000)
            
            # 4. Upload ảnh lên Cloudinary
            images_urls = {}
            for img_type, img_data in search_result["images"].items():
                cloudinary_url = upload_to_cloudinary(img_data, apartment_ch_id, img_type, 2000)
                images_urls[img_type] = cloudinary_url
            
            # 5. Tạo prompt cho OpenAI
            apartment_info = {
                "mã_căn": selected_apartment["Mã căn"],
                "ch_id": apartment_ch_id,
                "phân_khu": selected_apartment["PHÂN KHU"],
                "tầng": selected_apartment["Tầng"],
                "căn_số": selected_apartment["Căn STT"],
                "loại_hình": selected_apartment["Loại hình"],
                "diện_tích_tim_tường": selected_apartment["DT tim tường"],
                "diện_tích_thông_thủy": selected_apartment["DT thông thủy"],
                "giá": selected_apartment["Tổng giá trước VAT + KPBT"],
                "là_căn_góc": selected_apartment["căn góc"],
                "tổng_căn_tìm_được": len(filtered_apartments)
            }
            
            prompt = f"""
            Bạn là chuyên viên tư vấn bất động sản chuyên nghiệp. Hãy trả lời một cách thân thiện và chi tiết về căn hộ sau:

            Thông tin căn hộ:
            - Mã căn: {apartment_info['mã_căn']} (Căn số {apartment_info['căn_số']})
            - Phân khu: {apartment_info['phân_khu']}
            - Tầng: {apartment_info['tầng']}
            - Loại hình: {apartment_info['loại_hình']}
            - Diện tích tim tường: {apartment_info['diện_tích_tim_tường']} m²
            - Diện tích thông thủy: {apartment_info['diện_tích_thông_thủy']} m²
            - Giá: {self.format_price(apartment_info['giá'])}
            - Căn góc: {'Có' if apartment_info['là_căn_góc'] else 'Không'}

            Câu hỏi của khách hàng: "{user_query}"

            Tìm được {apartment_info['tổng_căn_tìm_được']} căn phù hợp, đây là thông tin chi tiết căn đầu tiên.

            Hãy trả lời một cách chuyên nghiệp, nêu rõ ưu điểm của căn hộ này và tại sao phù hợp với yêu cầu của khách hàng.
            Trả lời bằng tiếng Việt, khoảng 100-150 từ.
            """
            
            # 6. Gọi OpenAI
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Bạn là chuyên viên tư vấn bất động sản chuyên nghiệp và thân thiện."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # 7. Trả về kết quả
            return {
                "success": True,
                "message": ai_response,
                "apartment_info": {
                    "mã_căn": apartment_info["mã_căn"],
                    "ch_id": apartment_ch_id,
                    "phân_khu": apartment_info["phân_khu"],
                    "tầng": apartment_info["tầng"],
                    "loại_hình": apartment_info["loại_hình"],
                    "diện_tích_tim_tường": apartment_info["diện_tích_tim_tường"],
                    "diện_tích_thông_thủy": apartment_info["diện_tích_thông_thủy"],
                    "giá_formatted": self.format_price(apartment_info["giá"]),
                    "căn_góc": apartment_info["là_căn_góc"]
                },
                "images_urls": images_urls,
                "total_found": len(filtered_apartments)
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Có lỗi xảy ra khi xử lý yêu cầu: {str(e)}",
                "apartments": [],
                "images": []
            }

@app.post("/chat")
async def chat_endpoint(request: Dict):
    """
    🤖 Chat với AI để tìm kiếm căn hộ thông minh
    
    Body:
    {
        "query": "cho tôi thông tin căn góc tầng 2 phân khu Origami"
    }
    """
    try:
        user_query = request.get("query", "").strip()
        
        if not user_query:
            raise HTTPException(status_code=400, detail="Query không được để trống")
        
        searcher = get_searcher()
        chat_agent = ChatAgent(searcher)
        
        result = await chat_agent.process_query(user_query)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Apartment Search API...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)