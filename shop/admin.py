from django.contrib import admin
from .models import Product, Order, OrderItem

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """상품 관리 페이지"""
    list_display = ['name', 'price', 'stock', 'views', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    ordering = ['-created_at']

class OrderItemInline(admin.TabularInline):
    """주문 상세를 주문 페이지에 인라인으로 표시"""
    model = OrderItem
    extra = 0  # 빈 폼 개수
    readonly_fields = ['product', 'quantity', 'price']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """주문 관리 페이지"""
    list_display = ['customer_name', 'total_price', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['customer_name', 'customer_email']
    inlines = [OrderItemInline]
    ordering = ['-created_at']
