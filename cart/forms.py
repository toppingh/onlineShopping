from django import forms

# 장바구니에 제품을 추가하기 위한 폼
class AddProductForm(forms.Form):
    quantity = forms.IntegerField() # 수량
    # 상세 페이지에서 장바구니에 제품을 축할 때와 장바구니에서 수량을 변경할때 동작
    is_update = forms.BooleanField(required=False, initial=False, widget=forms.HiddenInput)