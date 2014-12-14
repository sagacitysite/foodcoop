from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns(
    '',
    url(r'^$', views.BundleListView.as_view(), name='order_bundle_list'),
    url(r'^bundle/newest/$', views.NewestBundleView.as_view(), name='order_bundle_newest'),
    url(r'^bundle/new/$', views.BundleCreateView.as_view(), name='order_bundle_create'),
    url(r'^bundle/(?P<pk>\d+)/$', views.BundleDetailView.as_view(), name='order_bundle_detail'),
    url(r'^bundle/(?P<pk>\d+)/del/$', views.BundleDeleteView.as_view(), name='order_bundle_delete'),
    url(r'^bundle/(?P<pk>\d+)/close/$', views.BundleCloseView.as_view(open=False), name='order_bundle_close'),
    url(r'^bundle/(?P<pk>\d+)/open/$', views.BundleCloseView.as_view(open=True), name='order_bundle_open'),
    url(r'^bundle/(?P<pk>\d+)/order/$', views.BundleOrderView.as_view(), name='order_bundle_order'),
    url(r'^bundle/(?P<pk>\d+)/output/$', views.BundleOutputView.as_view(), name='order_bundle_output'),

    url(r'^product/(?P<pk>\d+)/$', views.ProductUpdateView.as_view(), name='order_product_update'),
    url(r'^product/edit/$', views.ProductFormSetView.as_view(), name='order_product_formset'),

    url(r'^group/$', views.GroupListView.as_view(), name='order_group_list'),
    url(r'^group/new/$', views.GroupCreateView.as_view(), name='order_group_create'),
    url(r'^group/(?P<pk>\d+)/edit/$', views.GroupUpdateView.as_view(), name='order_group_update'),
    url(r'^group/(?P<pk>\d+)/del/$', views.GroupDeleteView.as_view(), name='order_group_delete'),
)
