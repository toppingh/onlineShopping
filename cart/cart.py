from decimal import Decimal

import requests
from django.conf import settings
from shop.models import Product
from coupon.models import Coupon

class Cart(object):
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_ID) # settings에 CART_ID와 연결
        if not cart : # cart 정보가 없으면
            cart = self.session[settings.CART_ID] = {} # 새 딕셔너리 생성
        self.cart = cart
        self.coupon_id = self.session.get('coupon_id') # 쿠폰 추가

    def __len__(self): # 장바구니에 있는 상품의 수량을 전부 더한 결과
        return sum(item['quantity'] for item in self.cart.values())

    def __iter__(self): # for문 사용시 어떤 요소를 건내줄지 지정
        product_ids = self.cart.keys() # 제품 번호 목록을 가져옴

        products = Product.objects.filter(id__in=product_ids) # 장바구니에 있는 제품 정보만 Product db에서 가져옴

        for product in products: # 제품 정보를 하나씩 읽어와서
            self.cart[str(product.id)]['product'] = product # session에 키 값들을 넣을 때 문자로 넣는다

        for item in self.cart.values(): # 장바구니에 있는 제품을 하나씩 꺼내
            item['total_price'] = item['price'] * item['quantity'] # 가격 x item 수를 총 가격에 넣고
            item['price'] = Decimal(item['price']) # 가격에 숫자형으로 바꿔 item에 넣는다

            yield item

    # 장바구니에 넣기
    def add(self, product, quantity=1, is_update=False): # 제품 정보를 업데이트하는지 아닌지 확인
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] = {'quantity':0, 'price':str(product.price)}

        if is_update:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity
        self.save()

    # 장바구니 저장하기
    def save(self):
        self.session[settings.CART_ID] = self.cart
        self.session.modified = True

    # 장바구니에서 삭제하기
    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart: # 장바구니에 제품이 있다면
            del(self.cart[product_id]) # 해당하는 제품을 삭제하고
            self.save() # 현재 장바구니를 저장한다

    # 장바구니 비우기
    def clear(self):
        self.session[settings.CART_ID] = {}
        self.session['coupon_id'] = None # 쿠폰 추가
        self.session.modified = True

    # 장바구니에 있는 제품의 총 가격 계산
    def get_product_total(self):
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    # 쿠폰 기능 추가
    @property
    def coupon(self):
        if self.coupon_id:
            return Coupon.objects.get(id=self.coupon_id)
        return None

    # 할인 금액
    def get_discount_total(self):
        if self.coupon:
            if self.get_product_total() >= self.coupon.amount:
                return self.coupon.amount
        return Decimal(0)

    # 총 금액
    def get_total_price(self):
        return self.get_product_total() - self.get_discount_total()