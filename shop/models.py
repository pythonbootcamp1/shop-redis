from django.db import models

class Product(models.Model):
    """상품 모델

    Redis 개선 포인트:
    - views 필드: 매번 DB UPDATE → Redis INCR로 개선 예정
    """
    name = models.CharField(
        max_length=200,
        verbose_name="상품명"
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        verbose_name="가격"
    )

    stock = models.IntegerField(
        default=0,
        verbose_name="재고"
    )

    # 🔴 성능 병목 지점 1: 조회수
    # 매번 상품을 볼 때마다 DB에 UPDATE 쿼리 발생
    # → 가이드 6에서 Redis INCR로 개선
    views = models.IntegerField(
        default=0,
        verbose_name="조회수"
    )

    description = models.TextField(
        verbose_name="상품 설명"
    )

    image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True,
        verbose_name="상품 이미지"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="등록일"
    )

    class Meta:
        verbose_name = "상품"
        verbose_name_plural = "상품"
        ordering = ['-created_at']  # 최신순 정렬

    def __str__(self):
        return self.name

class Order(models.Model):
    """주문 모델"""

    STATUS_CHOICES = [
        ('pending', '주문 접수'),
        ('confirmed', '주문 확인'),
        ('shipped', '배송 중'),
        ('delivered', '배송 완료'),
        ('cancelled', '주문 취소'),
    ]

    customer_name = models.CharField(
        max_length=100,
        verbose_name="주문자명"
    )

    customer_email = models.EmailField(
        verbose_name="이메일"
    )

    customer_phone = models.CharField(
        max_length=20,
        verbose_name="연락처"
    )

    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        verbose_name="총 주문 금액"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="주문 상태"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="주문일시"
    )

    class Meta:
        verbose_name = "주문"
        verbose_name_plural = "주문"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer_name}의 주문 ({self.created_at.strftime('%Y-%m-%d')})"
        
class OrderItem(models.Model):
    """주문 상세 모델

    하나의 주문에 여러 상품이 포함될 수 있음
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="주문"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name="상품"
    )

    quantity = models.IntegerField(
        default=1,
        verbose_name="수량"
    )

    # 주문 당시의 가격을 저장 (상품 가격이 변경되어도 주문 내역은 유지)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        verbose_name="주문 당시 가격"
    )

    class Meta:
        verbose_name = "주문 상세"
        verbose_name_plural = "주문 상세"

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    def get_subtotal(self):
        """소계 계산"""
        return self.price * self.quantity
