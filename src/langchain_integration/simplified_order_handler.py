from typing import Dict, Any

from ..config import config
from .vectorstore import VectorStore

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class SimplifiedOrderHandler:
    """
    Simplified order handler that converts order intents to contact recommendations.
    Replaces complex order flow with simple contact-based approach.
    """

    def __init__(self):
        """Initialize the simplified order handler."""
        self.vector_store = None

    def _initialize_vector_store(self) -> None:
        """Initialize vector store if not already initialized."""
        if self.vector_store is None:
            self.vector_store = VectorStore()
            self.vector_store.initialize_vectorstore()

    def _search_product(self, product_query: str) -> Dict[str, Any]:
        """
        Search for product in the vector database.
        Reuses existing product search logic from order_tools.py

        Args:
            product_query: Product name or query to search for

        Returns:
            Dict containing search results with product info
        """
        try:
            self._initialize_vector_store()

            print(f"🔍 Searching for product: '{product_query}'")

            # Use direct Qdrant similarity search - bypass LangChain document ID issues
            query_vector = self.vector_store.get_vectorstore().embeddings.embed_query(
                product_query
            )

            # Search directly in Qdrant with payload
            search_results = self.vector_store.client.search(
                collection_name=self.vector_store.collection_name,
                query_vector=query_vector,
                limit=5,
                with_payload=True,
            )

            if not search_results:
                return {"found": False, "type": "not_found", "query": product_query}

            print(f"✅ Found {len(search_results)} search results")

            # Look for the best matching product with price
            for i, point in enumerate(search_results):
                if not (hasattr(point, "payload") and point.payload):
                    continue

                payload = point.payload
                name = payload.get("name", "")
                price = payload.get("price", "")
                page_content = payload.get("page_content", "")

                print(f"--- Result {i + 1} ---")
                print(f"Name: {name}")
                print(f"Price: {price}")
                print(f"Content preview: {page_content[:100]}...")

                # Check if this matches our search query
                query_lower = product_query.lower()
                is_match = (
                    query_lower in name.lower()
                    or query_lower in page_content.lower()
                    or any(
                        word in name.lower() or word in page_content.lower()
                        for word in query_lower.split()
                    )
                )

                if is_match and price:
                    print(f"✅ Found matching product: {name}")
                    print(f"✅ Price found: {price}")

                    # Ensure price is integer
                    processed_price = None
                    if isinstance(price, str):
                        try:
                            processed_price = int(
                                price.replace(".", "")
                                .replace(",", "")
                                .replace("đ", "")
                                .replace("VND", "")
                                .strip()
                            )
                        except (ValueError, AttributeError):
                            continue
                    elif isinstance(price, (int, float)) and price > 0:
                        processed_price = int(price)

                    if processed_price and processed_price > 0:
                        return {
                            "found": True,
                            "type": "available",
                            "name": name,
                            "price": processed_price,
                            "query": product_query,
                        }

            # If no product with price found, try to find any matching product
            for point in search_results:
                if not (hasattr(point, "payload") and point.payload):
                    continue

                payload = point.payload
                name = payload.get("name", "")
                page_content = payload.get("page_content", "")

                # Check if this matches our search query
                query_lower = product_query.lower()
                is_match = (
                    query_lower in name.lower()
                    or query_lower in page_content.lower()
                    or any(
                        word in name.lower() or word in page_content.lower()
                        for word in query_lower.split()
                    )
                )

                if is_match:
                    return {
                        "found": True,
                        "type": "no_business",
                        "name": name if name else "Sản phẩm đã tìm thấy",
                        "query": product_query,
                    }

            # No matching product found at all
            return {"found": False, "type": "not_found", "query": product_query}

        except Exception as e:
            print(f"💥 Error in _search_product: {e}")
            return {
                "found": False,
                "type": "error",
                "query": product_query,
                "error": str(e),
            }

    def _format_price(self, price: int) -> str:
        """Format price in Vietnamese style"""
        return f"{price:,}".replace(",", ".")

    def handle_order_intent(self, product_query: str) -> str:
        """
        Handle order intent by searching product and returning contact recommendation.

        Args:
            product_query: Product name or query customer wants to order

        Returns:
            Response message with contact information
        """
        try:
            # Search for product
            search_result = self._search_product(product_query)

            # Generate appropriate response based on search result
            return self.format_contact_response(search_result)

        except Exception as e:
            return f"Xin lỗi anh/chị, em gặp lỗi khi xử lý yêu cầu: {e}"

    def format_contact_response(self, search_result: Dict[str, Any]) -> str:
        """
        Format contact response based on search result.

        Args:
            search_result: Dictionary containing search results

        Returns:
            Formatted response message with contact information
        """
        shop_phone = config.shop_phone
        shop_email = config.shop_email
        shop_name = config.shop_name

        if not search_result["found"]:
            # Product not found
            if search_result["type"] == "error":
                return f"""Xin lỗi anh/chị, em gặp lỗi khi tìm kiếm sản phẩm.

📞 Để được hỗ trợ trực tiếp, anh/chị vui lòng liên hệ:
• Điện thoại: {shop_phone}
• Email: {shop_email}

Đội ngũ {shop_name} sẽ tư vấn chi tiết cho anh/chị ạ! 🙏"""

            return f"""Rất tiếc, em không tìm thấy sản phẩm '{search_result["query"]}' trong hệ thống của {shop_name} ạ.

📞 Để được tư vấn sản phẩm tương tự hoặc kiểm tra thêm, anh/chị vui lòng liên hệ trực tiếp:
• Điện thoại: {shop_phone}
• Email: {shop_email}

Chúng tôi có thể tư vấn nhiều sản phẩm khác phù hợp với nhu cầu của anh/chị! 🛍️"""

        elif search_result["type"] == "available":
            # Product available with price
            formatted_price = self._format_price(search_result["price"])
            return f"""📱 Sản phẩm: {search_result["name"]}
💰 Giá tại {shop_name}: {formatted_price}đ
✅ Tình trạng: Hiện đang có hàng

📞 Để đặt hàng và được tư vấn chi tiết, anh/chị vui lòng liên hệ trực tiếp:
• Điện thoại: {shop_phone}
• Email: {shop_email}

Chúng tôi sẽ hỗ trợ anh/chị về:
• Thông tin chi tiết sản phẩm
• Phương thức thanh toán
• Giao hàng và bảo hành
• Tư vấn sản phẩm phù hợp

Cảm ơn anh/chị đã quan tâm đến {shop_name}! 🙏"""

        elif search_result["type"] == "no_business":
            # Product found but not in business
            return f"""Rất tiếc, {shop_name} hiện không kinh doanh sản phẩm '{search_result["name"]}' ạ.

📞 Để được tư vấn sản phẩm thay thế hoặc tương tự, anh/chị vui lòng liên hệ:
• Điện thoại: {shop_phone}
• Email: {shop_email}

Chúng tôi có nhiều sản phẩm khác có thể phù hợp với nhu cầu của anh/chị! 🛍️"""

        else:
            # Default fallback
            return f"""📞 Để được hỗ trợ tốt nhất về sản phẩm '{search_result.get("query", "yêu cầu")}', anh/chị vui lòng liên hệ trực tiếp:
• Điện thoại: {shop_phone}
• Email: {shop_email}

Đội ngũ {shop_name} sẽ tư vấn chi tiết và hỗ trợ anh/chị một cách tốt nhất! 🙏"""
