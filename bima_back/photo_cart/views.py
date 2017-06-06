# -*- coding: utf-8 -*-

from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.generic.base import View


class AddPhotoCart(View):
    """
    Adds a photo in the session cart, keeping its title, thumbnail url and id.
    Returns the cart template rendered with the new photo.
    """

    def get(self, request, *args, **kwargs):
        cart = {}
        if 'cart' in self.request.session:
            cart = self.request.session['cart']

        photo_data = {
            'title': self.request.GET.get('title', ''),
            'thumbnail': self.request.GET.get('thumbnail', ''),
            'id': self.request.GET.get('id', ''),
        }
        cart[self.kwargs['pk']] = photo_data
        self.request.session['cart'] = cart
        data = render_to_string('bima_back/includes/photo_cart_aside.html', context={'cart': cart})
        return JsonResponse(data=data, safe=False)


class RemovePhotoCart(View):
    """
    Removes a photo from the session cart given its id.
    Returns the cart template rendered without this photo.
    """

    def get(self, request, *args, **kwargs):
        cart = self.request.session['cart']
        cart.pop(str(self.kwargs['pk']))
        self.request.session['cart'] = cart
        data = render_to_string('bima_back/includes/photo_cart_aside.html', context={'cart': cart})
        return JsonResponse(data=data, safe=False)


class RemoveMultiplePhotoCart(View):
    """
    Empties the session photo cart and returns the empty rendered template.
    """

    def get(self, request, *args, **kwargs):
        cart = self.request.session['cart']
        photos = self.request.GET.get('ids', []).split(",")
        for photo in photos:
            if photo in cart:
                cart.pop(photo)
        self.request.session['cart'] = cart
        data = render_to_string('bima_back/includes/photo_cart_aside.html', context={'cart': cart})
        return JsonResponse(data=data, safe=False)
