from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import hashlib

from coupon.models import Coupon
from shop.models import Product
from .iamport import payments_prepare, find_transaction

# Create your models here.
# 주문 정보를 저장하는 모델
class Order(models.Model):
    first_name = models.CharField(max_length=50, null=False)
    last_name = models.CharField(max_length=50, null=False)
    phone = models.CharField(max_length=23)
    email = models.EmailField()
    address = models.CharField(max_length=250)
    msg = models.CharField(max_length=100)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    paid = models.BooleanField(default=False)

    coupon = models.ForeignKey(Coupon, on_delete=models.PROTECT,
                               related_name='order_coupon', null=True, blank=True)
    discount = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100000)])

    class Meta:
        ordering = ['created']

    def __str__(self):
        return 'Order {}'.format(self.id)

    # 전체 물건 가격 (할인 적용 전)
    def get_total_product(self):
        return sum(item.get_item_price() for item in self.items.all())

    # 전체 물건 가격 (할인 적용 후)
    def get_total_price(self):
        total_product = self.get_total_product()
        return total_product - self.discount

# 주문에 포함된 제품의 정보를 담기 위해 만드는 모델
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_products')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return '{}'.format(self.id)

    def get_item_price(self):
        return self.price * self.quantity

# OrderTransaction 모델의 매니저 클래스
class OrderTransactionManager(models.Manager):
    def create_new(self, order, amount, success=None, transaction_status=None):
        if not order:
            raise ValueError("주문 오류")

        # 해시 함수를 사용해 merchant_order_id 생성
        order_hash = hashlib.sha1(str(order.id).encode('utf-8')).hexdigest()
        email_hash = str(order.email).split("@")[0]
        final_hash = hashlib.sha1((order_hash + email_hash).encode('utf-8')).hexdigest()[:10]
        merchant_order_id = "%s" % (final_hash)

        payments_prepare(merchant_order_id, amount)

        # self.model은 OrderTransaction 의미
        transaction = self.model(
            order=order,
            merchant_order_id = merchant_order_id,
            amount=amount
        )

        if success is not None:
            transaction.success = success
            transaction.transcation_status = transaction_status

        try:
            transaction.save()
        except Exception as e:
            print("save error", e)

        return transaction.merchant_order_id

    def get_transaction(selfself, merchant_order_id):
        result = find_transaction(merchant_order_id)
        if result['status'] == 'paid':
            return result
        else:
            return None

# 결제 정보를 저장할 때 사용하는 모델
class OrderTransaction(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    # 서버에서 자동 생성되는 포트원 쪽으로 결체요청할때 필요한 주문번호
    merchant_order_id = models.CharField(max_length=120, null=True, blank=True)
    # 포트원에서 생성해주는 고유번호
    transaction_id = models.CharField(max_length=120, null=True, blank=True)
    amount = models.PositiveIntegerField(default=0)
    transaction_status = models.CharField(max_length=220, null=True, blank=True)
    type = models.CharField(max_length=120, blank=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)

    objects = OrderTransactionManager()

    def __str__(self):
        return str(self.order.id)

    class Meta:
        ordering = ['-created']

# 시그널을 활용한 결제 검증 함수
def order_payment_validation(sender, instance, created, *args, **kwargs):
    # transaction_id가 존재하느 경우에만 실행
    if instance.transaction_id:
        # merchant_order_id를 이용해 포트원에서 transaction을 요청해 얻어옴
        iamport_transaction = OrderTransaction.objects.get_transaction(merchant_order_id=instance.merchant_order_id)

        merchant_order_id = iamport_transaction['merchant_order_id']
        imp_id = iamport_transaction['imp_id'] # 결제 모듈 측의 id
        amount = iamport_transaction['amount']

        # Order Transaction model에 저장된 transaction 읽어옴
        local_transaction = OrderTransaction.objects.filter(merchant_order_id=merchant_order_id,
                                                            transaction_id = imp_id, amount=amount).exists()

        # 포트원에서 요청해 받아온 transaction, DB에 저장된 transaction 확인
        if not iamport_transaction or not local_transaction:
            raise ValueError("비정상 거래입니다.")

from django.db.models.signals import post_save
post_save.connect(order_payment_validation, sender=OrderTransaction)