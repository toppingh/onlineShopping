import requests

from django.conf import settings

# 포트원 서버와 통신을 위한 토큰을 받아오는 함수
# 발급받은 토큰으로 유저가 결제한 정보 가져옴
def get_token():
    access_data = {
        'imp_key' : settings.IAMPORT_KEY,
        'imp_secret' : settings.IAMPORT_SECRRET
    }

    url = "https://api.iamport.kr/users/getToken"

    # requests 모듈 -> API키와 API secret 키를 psot 형식으로 요청
    req = requests.post(url, data=access_data)
    access_res = req.json()

    if access_res['code'] is 0:
        return access_res['response']['access_token']
    else:
        return None

# 결제 준비 함수
# 결제 검증 단계(유저의 요청 금액과 포트원의 결제 금액이 일치하는지 검증)
def payments_prepare(order_id, amount, *args, **kwargs):
    access_token = get_token()
    if access_token:
        access_data = {
            'merchant_uid':order_id,
            'amount':amount
        }
        url = "https://api.iamport.kr/payments/prepare"
        headers = {
            'Authorization':access_token
        }
        req = requests.post(url, data=access_data, headers=headers)
        res = req.json()

        if res['code'] is not 0:
            raise ValueError("API 통신 오류")
    else:
        raise ValueError("토큰 오류")

# 결제 완료 후 실제 결제가 이뤄진 것이 맞는지 확인하는 함수
# 결제 완료 후 결제 정보를 가져옴
def find_transaction(order_id, *args, **kwargs):
    access_token = get_token()
    if access_token:
        url = "https://api.iamport.kr/payments/find/"+order_id

        headers = {
            'Authorization':access_token
        }

        req = requests.post(url, headers=headers)
        res = req.json()

        if res['code'] is 0:
            context = {
                'imp_id':res['response']['imp_uid'],
                'merchant_order_id':res['response']['merchant_uid'],
                'amount':res['response']['amount'],
                'status':res['response']['status'],
                'type':res['response']['pay_method'],
                'receipt_url':res['response']['receipt_url']
            }
            return context
        else:
            return None
    else:
        raise ValueError("토큰 오류")

# 결제 오류 디버깅
def get_token():
    access_data = {
        'imp_key': settings.IAMPORT_KEY,
        'imp_secret': settings.IAMPORT_SECRET
    }

    url = "https://api.iamport.kr/users/getToken"

    req = requests.post(url, data=access_data)
    access_res = req.json()

    print('get_token()--(1) : ', access_res) # access_res 값 확인해보기

    if access_res['code'] is 0:
        return access_res['response']['access_token']
    else:
        return None