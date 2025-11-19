from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.views import View
from django.contrib import messages
from django.db.models import F
from django.db import transaction
from django.core.cache import cache
from .models import Product, Order, OrderItem
import json

class ProductListView(ListView):
    """상품 목록 뷰

    Django의 제네릭 뷰(Generic View) 사용
    - 자주 사용하는 패턴을 미리 구현해둔 클래스 기반 뷰
    - 코드 양을 줄이고 일관성을 높일 수 있음
    """
    model = Product
    template_name = 'shop/product_list.html'
    context_object_name = 'products'
    paginate_by = 12  # 한 페이지에 12개씩 표시
    # return render(request, 'shop/product_list.html', {'products': products})

    def get_queryset(self):
        """상품 목록 가져오기"""
        return Product.objects.filter(stock__gt=0)  # 재고가 있는 상품만


class ProductDetailView(DetailView):
    """상품 상세 페이지 (Redis 캐싱 적용)"""

    model = Product
    template_name = 'shop/product_detail.html'

    def get_object(self):
        product_id = self.kwargs['pk']

        # 1. 캐시 키 생성
        cache_key = f"product:{product_id}"

        # 2. 캐시 확인
        cached_product = cache.get(cache_key)

        if cached_product:
            # 캐시 히트!
            print(f"✅ 캐시에서 조회: {cache_key}")
            return cached_product

        # 3. 캐시 미스 → DB 조회
        print(f"⚠️ DB 조회: {cache_key}")
        product = super().get_object()

        # 4. 캐시에 저장 (5분)
        cache.set(cache_key, product, timeout=300)

        return product

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object

        # 조회수 증가 (Redis 카운터 사용)
        views_key = f"product:{product.id}:views"
        # incr을 사용할 때 views_key가 없으면 None을 반환하거나 에러가 날 수 있음. 미리 0으로 초기화 후 증가
        if cache.get(views_key) is None:
            cache.set(views_key, 0, timeout=None)
        views = cache.incr(views_key, delta=1)

        context['views'] = views

        return context

class AddToCartView(View):
    """장바구니 추가

    🔴 성능 개선 포인트!
    세션은 기본적으로 파일로 저장됨 → 느림
    → 가이드 6에서 Redis Session으로 개선
    """

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        quantity = int(request.POST.get('quantity', 1))

        # 재고 확인
        if quantity > product.stock:
            messages.error(request, f'{product.name}의 재고가 부족합니다.')
            return redirect('shop:product_detail', pk=pk)

        # 세션에서 장바구니 가져오기 (없으면 빈 딕셔너리)
        # 🔴 세션 파일 I/O 발생 → 느림
        cart = request.session.get('cart', {})

        # 장바구니에 상품 추가 또는 수량 증가
        product_id = str(pk)
        if product_id in cart:
            cart[product_id]['quantity'] += quantity
        else:
            cart[product_id] = {
                'name': product.name,
                'price': float(product.price),
                'quantity': quantity
            }

        # 🔴 세션 저장 → 파일 I/O 발생
        request.session['cart'] = cart
        request.session.modified = True

        messages.success(request, f'{product.name}을(를) 장바구니에 담았습니다.')
        return redirect('shop:product_detail', pk=pk)


class CartView(View):
    """장바구니 보기"""

    def get(self, request):
        # 🔴 세션 읽기 → 파일 I/O 발생
        cart = request.session.get('cart', {})

        # 총액 계산
        total = sum(item['price'] * item['quantity'] for item in cart.values())

        context = {
            'cart': cart,
            'total': total
        }
        return render(request, 'shop/cart.html', context)
class CheckoutView(View):
    """주문하기"""

    def get(self, request):
        cart = request.session.get('cart', {})
        if not cart:
            messages.warning(request, '장바구니가 비어있습니다.')
            return redirect('shop:product_list')

        total = sum(item['price'] * item['quantity'] for item in cart.values())
        context = {
            'cart': cart,
            'total': total
        }
        return render(request, 'shop/checkout.html', context)

    def post(self, request):
        cart = request.session.get('cart', {})
        if not cart:
            messages.warning(request, '장바구니가 비어있습니다.')
            return redirect('shop:product_list')

        customer_name = request.POST.get('customer_name')
        customer_email = request.POST.get('customer_email')
        customer_phone = request.POST.get('customer_phone')

        # 🔴 재고 감소 로직 - 동시성 문제 발생 가능!
        # → 가이드 5에서 문제 발견
        # → 가이드 7에서 Redis Lua Script로 해결

        try:
            with transaction.atomic():
                # 총액 계산
                total = sum(item['price'] * item['quantity'] for item in cart.values())

                # 주문 생성
                order = Order.objects.create(
                    customer_name=customer_name,
                    customer_email=customer_email,
                    customer_phone=customer_phone,
                    total_price=total
                )

                # 주문 상세 생성 및 재고 감소
                for product_id, item in cart.items():
                    product = Product.objects.get(pk=product_id)

                    # 재고 확인
                    if product.stock < item['quantity']:
                        messages.error(request, f'{product.name}의 재고가 부족합니다.')
                        return redirect('shop:cart')

                    # 주문 상세 생성
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=item['quantity'],
                        price=item['price']
                    )

                    # 🔴 재고 감소 - 동시 주문 시 문제 발생!
                    product.stock -= item['quantity']
                    product.save()

                # 장바구니 비우기
                request.session['cart'] = {}
                request.session.modified = True

            messages.success(request, '주문이 완료되었습니다!')
            return redirect('shop:order_complete', order_id=order.pk)

        except Exception as e:
            messages.error(request, f'주문 처리 중 오류가 발생했습니다: {str(e)}')
            return redirect('shop:cart')


class OrderCompleteView(View):
    """주문 완료"""

    def get(self, request, order_id):
        order = get_object_or_404(Order, pk=order_id)
        context = {'order': order}
        return render(request, 'shop/order_complete.html', context)
