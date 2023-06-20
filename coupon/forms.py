from django import forms

# 쿠폰을 폼을 통해 데이터 전달
class AddCouponForm(forms.Form):
    code = forms.CharField(label='쿠폰 코드 입력')