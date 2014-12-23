from collections import defaultdict
import json

from django.core.urlresolvers import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, UpdateView, CreateView, RedirectView, DeleteView
from django.views.generic.detail import SingleObjectMixin
from django.http import HttpResponse
from django.db.models import Sum
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
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
        self.object = self.get_object()  # TODO: this is called twice

        # It is not possible to alter orders on closed bundles
        if not self.object.open:
            raise PermissionDenied()

        self.active_group = self.get_active_group(request)
        if request.is_ajax():
            return self.ajax(request, *args, **kwargs)
        else:
            # Call super().get() because a DetailView does not have a post-method.
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
        """
        Returns a list of all available products with extra attributes.

        This extra attributes are in particular a OrderForm.

        Validates this forms, if self.request is a post-request.
        """
        products = Product.objects.filter(available=True).select_related()

        # Order-data can only be used, if there is an active_group
        if self.active_group is not None:
            query = Order.objects.filter(bundle=self.object, group=self.active_group)
            # Create a hashtable, of products hashed from there products
            order_dict = dict((order.product, order) for order in query)

            for product in products:
                prefix = "p{}".format(product.pk)
                form_kwargs = {'prefix': prefix, 'instance': order_dict.get(product, None)}
                if self.request.method == 'POST':
                    product.form = OrderForm(self.request.POST, **form_kwargs)
                    if product.form.is_valid():
                        order = product.form.save(commit=False)
                        order.group = self.active_group
                        order.bundle = self.object
                        order.product = product
                        order.save()
                else:
                    product.form = OrderForm(**form_kwargs)
        return products

    def get_context_data(self, **context):
        """
        Returns extra context for the view.

        * products = a list of all available products
        * group_from = form to choose the active_group
        * active_group = the active_group
        * price_for_group = the costs for the active_group
        * price_unknown = True, if not all ordered products have a price
        """
        return super().get_context_data(
            products=self.get_products(),
            group_form=GroupChooseForm(initial={'group': self.active_group}),
            active_group=self.active_group,
            price_for_group="{:.2f}".format(self.object.price_for_group(self.active_group)),
            price_unknown=self.object.has_unknown_price(self.active_group),
            **context)


class BundleCreateView(RedirectView):
    """
    View to create a Bundle.

    This view does not show a form, but creates the bundle on the fly.
    """

    permanent = False
    pattern_name = 'order_bundle_list'

    def get(self, *args, **kwargs):
        Bundle.objects.create()
        return super().get(*args, **kwargs)


class BundleDeleteView(DeleteView):
    """
    View to delete a bundle.
    """
    model = Bundle
    success_url = reverse_lazy('order_bundle_list')


class BundleCloseView(SingleObjectMixin, RedirectView):
    """
    View to close a bundle, so no orders can be send to the bundle anymore.
    """

    permanent = False
    model = Bundle
    open = False

    def get(self, *args, **kwargs):
        self.bundle = self.get_object()  # TODO: this is propably called twice
        self.bundle.open = self.open
        self.bundle.save()
        return super().get(*args, **kwargs)

    def get_redirect_url(self, *args, **kwarts):
        return self.bundle.get_absolute_url()


class NewestBundleView(RedirectView):
    """
    Redirects to the DetailView of the newest bundle.
    """

    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        try:
            return Bundle.objects.latest().get_absolute_url()
        except Bundle.DoesNotExist:
            return reverse('order_bundle_list')


class BundleOrderView(DetailView):
    """
    DetailView of a Bundle, to see summary of all orders, for ordering all the
    products from the distributor.
    """

    model = Bundle
    template_name = 'order/bundle_detail_order.html'

    def get_products(self):
        """
        Returns all products for that is at least one order in this bundle.

        The returned object is a list that is ordered by the product name. To each
        product-object two attributes are appended.
        * amount: the amount of ordered units for this product in this bundle
        * order_price: the price for the order of this product for this bundle
        """
        # Generates a dict to save for each product the ordered amount.
        products_dict = defaultdict(int)
        for order in self.object.orders.all().select_related():
            products_dict[order.product] += order.amount

        products = list()
        for product, amount in products_dict.items():
            if amount > 0:
                product.amount = amount
                product.order_price = product.multiplier * amount
                products.append(product)

        products.sort(key=lambda product: product.name)

        return products

    def get_context_data(self, **context):
        """
        Returns all products and the price for all products as extra context.
        """
        products = self.get_products()
        return super().get_context_data(
            products=products,
            order_price=sum(product.order_price for product in products),
            **context)


class BundleOutputView(DetailView):
    """
    DetailView to show all orders of a bundle, so the products can be
    distributed.

    This view is also used to save the actually send products via ajax.
    """

    model = Bundle
    template_name = 'order/bundle_detail_output.html'

    def post(self, request, *args, **kwargs):
        """
        This view can only called via post, if it is an ajax-request.

        Raise PermissionDenied in other case.
        """
        # TODO: Find a better error then PermissionDenied
        if not request.is_ajax():
            raise PermissionDenied()

        self.object = self.get_object()
        return self.ajax(request, *args, **kwargs)

    def ajax(self, request, *args, **kwargs):
        """
        Save the actual delivered amount from one product to one group.

        The group is not the active_group, but received in the post-data.

        The expected data is in the form:
        group: id
        product: id
        delivered: int (e.G. 500)

        The response is in json, for excample:
        {'price_for_group': 5.45,
         'price_for_all': 10.34,
         'product_delivered': 23}
        where product_delivered is the total delivered amount (for all groups)
        """
        # TODO: calculate the price and the delivered amount in JS
        try:
            product = Product.objects.get(pk=request.POST['product'])
            group = Group.objects.get(pk=request.POST['group'])
        except ObjectDoesNotExist:
            return_data = {'error': "Group or product not found"}
        except KeyError:
            return_data = {'error': "No product or group data in request"}
        else:
            # Create the order-object if necessary
            order, __ = Order.objects.get_or_create(product=product, bundle=self.object, group=group)
            try:
                order.delivered = request.POST['delivered']
            except KeyError:
                return_data = {'error': "No amount data in request"}
            else:
                order.save()  # TODO: try to use update()

                # Calculate the total delivered amount for that product
                query = Order.objects.filter(product=product, bundle=self.object)
                product_delivered = query.aggregate(delivered=Sum('delivered'))['delivered']
                return_data = {
                    'price_for_group': "{:.2f}".format(self.object.price_for_group(group, delivered=True)),
                    'price_for_all': "{:.2f}".format(self.object.price_for_all(delivered=True)),  # TODO: rename to price_for_all
                    'product_delivered': product_delivered}
        return HttpResponse(json.dumps(return_data))

    def get_context_data(self, **context):
        """
        Returns extra context for the view:
        * products: sorted list with all products, where at least one is ordered
                    each product has an extra attribute 'delivered' which is the
                    actual delivered amount of the product.

        * groups:   dict where the key is a group-object and value is a two-value
                    list where the first element is a dict and the second element
                    the price the group has to pay. The key of the inner dict is
                    is an product-object and the value the relevant order-object.

        * price_for_all: the prive for this bundle
        """
        # Dict where key=group, value=[group_inner_dict, price_for_group]
        # and group_inner_dict is key=product, value=order
        # e.G: {group1: [{product1: order, product2: order, ...}, 34.12], {group2: [....]}, ...}
        # TODO: make a defaultdict with specific create function
        group_dict = dict()

        # Temporary dict where key=product, value=[delivered_for_all, ordered_for_all]
        product_dict = defaultdict(lambda: [0, 0])
        for order in self.object.orders.all().select_related():
            # get group_dict for specific group in order_dict or create it.
            try:
                group_inner_dict = group_dict[order.group][0]
            except KeyError:
                group_dict[order.group] = [dict(), 0]
                group_inner_dict = group_dict[order.group][0]

            # Connect order with group
            group_inner_dict[order.product] = order
            group_dict[order.group][1] += order.get_delivered() * order.product.multiplier

            product_dict[order.product][0] += order.get_delivered()
            product_dict[order.product][1] += order.amount

        # Create a list of all products where each product has an extra argument
        # 'delivered' which is the amount of all delivered units of this product.
        products = list()
        for product, order_values in product_dict.items():
            if order_values[1] > 0:  # ordered amount > 0
                product.delivered = order_values[0]  # delivered
                products.append(product)
        products.sort(key=lambda product: product.name)

        return super().get_context_data(
            products=products,
            price_for_all=sum(group[1] for group in group_dict.values()),
            groups=group_dict,
            **context)


class ProductUpdateView(UpdateView):
    """
    View to update one product.
    """
    model = Product


class ProductFormSetView(ModelFormSetView):
    """
    View to update all products, and add new ones.
    """
    model = Product
    template_name = 'order/product_formset.html'
    can_delete = True
    extra = 20


class GroupListView(ListView):
    """
    List all groups.
    """
    model = Group


class GroupCreateView(CreateView):
    """
    Create new groups.
    """
    model = Group


class GroupUpdateView(UpdateView):
    """
    Update existing groups.
    """
    model = Group


class GroupDeleteView(DeleteView):
    """
    Delete groups.
    """
    model = Group
    success_url = reverse_lazy('order_group_list')
