from collections import defaultdict
import json

from django.core.urlresolvers import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, UpdateView, CreateView, RedirectView, DeleteView
from django.views.generic.detail import SingleObjectMixin
from django.http import HttpResponse
from django.db.models import Sum
from django.core.exceptions import ObjectDoesNotExist
from extra_views import ModelFormSetView

from .models import Bundle, Product, Group, Order
from .forms import GroupChooseForm, OrderForm


class BundleListView(ListView):
    """
    View to show all Bundles.
    """

    model = Bundle


class BundleDetailView(DetailView):
    """
    View to show one Bundle.

    This view is used to save the order. It has functionality to send a form to
    django, or to send data via ajax.
    """

    model = Bundle

    def get(self, request, *args, **kwargs):
        """
        Starter method if the view is requested with a get-request.
        """
        self.active_group = self.get_active_group(request)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Starter method if the view is requested with a post-request.

        This is the case if the order-form is submitted, or if data is send via
        ajax.
        """
        self.active_group = self.get_active_group(request)
        if request.is_ajax():
            # self.object is filled in self.get or self.post, which are not called here
            self.object = self.get_object()
            return self.ajax(request, *args, **kwargs)
        else:
            return super().get(request, *args, **kwargs)

    def get_active_group(self, request):
        """
        Get the active_group.

        Use either the GET-arguments or the group, saved in the session.
        Returns the active Group or None.
        """
        # Try to use the GET-Data
        group_form = GroupChooseForm(request.GET)
        if group_form.is_valid():
            active_group = group_form.cleaned_data.get('group')
            request.session['active_group'] = active_group.pk

        # Try to use the session
        elif request.session.get('active_group', None):
            try:
                active_group = Group.objects.get(pk=request.session.get('active_group'))
            except Group.DoesNotExist:
                active_group = None

        # There are no data about the active group
        else:
            active_group = None
        return active_group

    def ajax(self, request, *args, **kwargs):
        """
        Receives the data via ajax.

        The expected data is the amount for one product for one product. Send more
        then one ajax-request to save more then one product.

        The response is json in the form:
        {'price_for_group': 5.49}
        """
        try:
            product = Product.objects.get(pk=request.POST['product'])
        except Product.DoesNotExist:
            return_data = {'error': "product {} not found".format(request.POST['product'])}
        except KeyError:
            return_data = {'error': "no product data in request"}
        else:
            # Create the Order-object if necessary
            order, __ = Order.objects.get_or_create(product=product, bundle=self.object, group=self.active_group)
            order.amount = int(request.POST['amount'])
            order.save()
            return_data = {'price_for_group': "{:.2f}".format(self.object.price_for_group(self.active_group))}

        return HttpResponse(json.dumps(return_data))

    def get_products(self):
        products = Product.objects.filter(available=True).select_related()

        if self.active_group is not None:
            query = Order.objects.filter(bundle=self.object, group=self.active_group)
            order_dict = dict((order.product, order) for order in query)

            for product in products:
                prefix = "p{}".format(product.pk)
                if self.request.method == 'POST':
                    product.form = OrderForm(self.request.POST, prefix=prefix, instance=order_dict.get(product, None))

                    if product.form.is_valid():
                        order = product.form.save(commit=False)
                        order.group = self.active_group
                        order.bundle = self.object
                        order.product = product
                        order.save()
                else:
                    product.form = OrderForm(prefix=prefix, instance=order_dict.get(product, None))
        return products

    def get_context_data(self, **context):
        return super().get_context_data(
            products=self.get_products(),
            group_form=GroupChooseForm(initial={'group': self.active_group}),
            active_group=self.active_group,
            costs="{:.2f}".format(self.object.price_for_group(self.active_group)),
            **context)


class BundleCreateView(RedirectView):
    permanent = False
    pattern_name = 'order_bundle_list'

    def get(self, *args, **kwargs):
        Bundle.objects.create()
        return super().get(*args, **kwargs)


class BundleDeleteView(DeleteView):
    model = Bundle
    success_url = reverse_lazy('order_bundle_list')


class BundleCloseView(SingleObjectMixin, RedirectView):
    permanent = False
    model = Bundle
    open = False

    def get(self, *args, **kwargs):
        self.bundle = self.get_object()
        self.bundle.open = self.open
        self.bundle.save()
        return super().get(*args, **kwargs)

    def get_redirect_url(self, *args, **kwarts):
        return self.bundle.get_absolute_url()


class NewestBundleView(RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        try:
            return Bundle.objects.latest().get_absolute_url()
        except Bundle.DoesNotExist:
            return reverse('order_bundle_list')


class BundleOrderView(DetailView):
    model = Bundle
    template_name = 'order/bundle_detail_order.html'

    def get_products(self):
        products_dict = defaultdict(int)
        for order in self.object.orders.all().select_related():
            products_dict[order.product] += order.amount

        products = list()
        for product, amount in products_dict.items():
            products.append(product)
            product.amount = amount
            product.order_price = product.multiplier * product.amount

        products.sort(key=lambda product: product.name)

        return products

    def get_context_data(self, **context):
        products = self.get_products()
        return super().get_context_data(
            products=products,
            order_price=sum(product.order_price for product in products),
            **context)


class BundleOutputView(DetailView):
    model = Bundle
    template_name = 'order/bundle_detail_output.html'

    def get_context_data(self, **context):
        order_dict = dict()
        products_dict = defaultdict(int)
        for order in self.object.orders.all().select_related():
            try:
                group_dict = order_dict[order.group][0]
            except KeyError:
                order_dict[order.group] = [dict(), 0]
                group_dict = order_dict[order.group][0]

            group_dict[order.product] = order
            order_dict[order.group][1] += order.get_delivered() * order.product.multiplier

            products_dict[order.product] += order.get_delivered()

        products = list()
        for product, delivered in products_dict.items():
            products.append(product)
            product.delivered = delivered

        products.sort(key=lambda product: product.name)

        return super().get_context_data(
            products=products,
            order_price=sum(order[1] for order in order_dict.values()),
            groups=order_dict.keys(),
            orders=order_dict,
            **context)

    def post(self, request, *args, **kwargs):
        if request.is_ajax():
            return self.ajax(request, *args, **kwargs)
        # TODO: Fehler schmeißen

    def ajax(self, request, *args, **kwargs):
        bundle = self.get_object()
        try:
            product = Product.objects.get(pk=request.POST['product'])
            group = Group.objects.get(pk=request.POST['group'])
        except ObjectDoesNotExist:
            pass  # TODO: send an error
        else:
            order, __ = Order.objects.get_or_create(product=product, bundle=bundle, group=group)
            order.delivered = request.POST['amount']
            order.save()
            query = Order.objects.filter(product=product, bundle=bundle)
            product_delivered = query.aggregate(delivered=Sum('delivered'))['delivered']
            return HttpResponse(json.dumps({
                'costs': "{:.2f}".format(bundle.price_for_group(group, delivered=True)),
                'price_all': "{:.2f}".format(bundle.price_for_all(delivered=True)),
                'product_delivered': product_delivered}))


class ProductUpdateView(UpdateView):
    model = Product


class ProductFormSetView(ModelFormSetView):
    model = Product
    template_name = 'order/product_formset.html'
    can_delete = True
    extra = 20


class GroupListView(ListView):
    model = Group


class GroupCreateView(CreateView):
    model = Group


class GroupUpdateView(UpdateView):
    model = Group


class GroupDeleteView(DeleteView):
    model = Group
    success_url = reverse_lazy('order_group_list')
