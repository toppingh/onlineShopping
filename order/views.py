import weasyprint
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.views.generic.base import View
from django.http import JsonResponse, HttpResponse
from django.contrib.admin.views.decorators import staff_member_required

from django.conf import settings
from .models import *
from cart.cart import Cart
from .forms import *

# Create your views here.
# js가 동작하지 않는 환경에서 동작(주문 가능하도록)
def order_create(request): # 주문서 입력 뷰, 장바구니에서 주문하기 클릭시 나오는 페이지
    cart = Cart(request)
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save()
            if cart.coupon:
                order.coupon = cart.coupon
                order.discount = cart.coupon.amount
                order.save()

            for item in cart:
                OrderItem.object.create(order=order, product=item['product'],
                                        price=item['price'], quantity=item['quantity'])
            cart.clear()

            return render(request, 'order/created.html', {'order':order})
    else:
        form = OrderCreateForm()

    return render(request, 'order/create.html', {'cart':cart, 'form':form})

# 주문 정보 입력 후 결제완료 시 주문 완료 화면 표시 뷰
def order_complete(request):
    order_id = request.GET.get('order_id')
    order = Order.objects.get(id=order_id)
    return render(request, 'order/created.html', {'order':order})

# 화면 전환 없이 js를 통해 호출되는 뷰
class OrderCreateAjaxView(View):
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated: # 로그인 하지 않은 경우
            return JsonResponse({"authenticated":False}, status=403)

        cart = Cart(request)

        # order_Create() 부분과 거의 동일
        form = OrderCreateForm(request.POST)

        if form.is_valid():
            order = form.save(commit=False)  # database 저장하는 query 보내지 않음
            if cart.coupon:
                order.coupon = cart.coupon
                order.discount = cart.coupon.amount

            order.save()  # database에 실제 query가 보내짐
            # order = form.save() # 교재의 코드를 위처럼 변경

            for item in cart:
                OrderItem.objects.create(order=order, product=item['product'],
                                         price=item['price'], quantity=item['quantity'])

            cart.clear()  # 카트비움

            data = {
                "order_id": order.id
            }
            return JsonResponse(data)

        else:
            return JsonResponse({}, status=401)

# 실제 결제 전 OrderTransaction 객체 생성 역할
class OrderCheckoutAjaxView(View):
    def post(self, request, *args, **kwargs):

        if not request.user.is_authenticated:
            return JsonResponse({"authenticated":False}, status=403)

        order_id = request.POST.get('order_id')
        order = Order.objects.get(id=order_id)
        amount = request.POST.get('amount')

        try:
            # transaction 생성
            merchant_order_id = OrderTransaction.objects.create_new(
                order=order,
                amount=amount
            )
        except:
            merchant_order_id = None

        if merchant_order_id is not None:
            data = {
                "works": True,
                "merchant_id": merchant_order_id
            }
            return JsonResponse(data)
        else:
            return JsonResponse({}, status=401)

# 실제 결제 완료 후 처리 부분, 결제 검증 뷰
class OrderImpAjaxView(View):
    def post(self, request, *args, **kwargs):

        if not request.user.is_authenticated:
            return JsonResponse({"authenticated":False}, status=403)

        order_id = request.POST.get('order_id')
        order = Order.objects.get(id=order_id)
        merchant_id = request.POST.get('merchant_id')
        imp_id = request.POST.get('imp_id')
        amount = request.POST.get('amount')

        try:
            trans = OrderTransaction.objects.get(
                order=order,
                merchant_order_id=merchant_id,
                amount=amount
            )
        except:
            trans = None

        if trans is not None:
            trans.transaction_id = imp_id
            trans.success = True
            trans.save()
            order.paid = True
            order.save()

            data = {
                "works": True
            }

            return JsonResponse(data)
        else:
            return JsonResponse({}, status=401) # unautorized error

@staff_member_required
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'order/admin/detail.html', {'order':order})

@staff_member_required
def admin_order_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    html = render_to_string('order/admin/pdf.html', {'order':order})
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'filename=order_{}.pdf'.format(order.id)
    weasyprint.HTML(string=html).write_pdf(response, stylesheets=[weasyprint.
                                           CSS(str(settings.STATICFILES_DIRS[0])+'/css/pdf.css')])
    return response