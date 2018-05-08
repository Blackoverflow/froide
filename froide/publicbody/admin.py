from __future__ import unicode_literals

from django.contrib import admin
from django.db.models import Count
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.urls import reverse_lazy
from django import forms
from django.urls import reverse
from django.utils.html import format_html

from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory

from froide.helper.admin_utils import (
    AdminTagAllMixIn, make_admin_assign_action, make_emptyfilter,
    make_nullfilter
)
from froide.helper.forms import get_fk_form_class
from froide.helper.widgets import TagAutocompleteWidget
from froide.helper.csv_utils import export_csv_response

from .models import (PublicBody, PublicBodyTag, TaggedPublicBody, FoiLaw,
                     Jurisdiction, Classification,
                     Category, CategorizedPublicBody)


CATEGORY_AUTOCOMPLETE_URL = reverse_lazy('api:category-autocomplete')


class PublicBodyAdminForm(forms.ModelForm):
    class Meta:
        model = PublicBody
        fields = '__all__'
        widgets = {
            'categories': TagAutocompleteWidget(
                autocomplete_url=CATEGORY_AUTOCOMPLETE_URL),
        }


ClassificationAssignMixin = make_admin_assign_action('classification')


class PublicBodyAdminMixin(ClassificationAssignMixin, AdminTagAllMixIn):
    form = PublicBodyAdminForm

    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        (None, {
            'fields': (
                'name', 'slug', 'other_names',
                'classification',
                'url', 'email', 'fax',
                'contact', 'address',
            )
        }),
        (_('Context'), {
            'fields': (
                'jurisdiction', 'laws',
                'request_note',
                'categories',
                'description',
                'file_index', 'org_chart',
            ),
        }),
        (_('Hierachy'), {
            'classes': ('collapse',),
            'fields': ('parent', 'root', 'depth'),
        }),
        (_('Geo'), {
            'classes': ('collapse',),
            'fields': ('geo', 'region'),
        }),
        (_('Advanced'), {
            'classes': ('collapse',),
            'fields': ('site', 'number_of_requests', 'website_dump'),
        }),
        (_('Meta'), {
            'fields': ('_created_by', 'created_at', '_updated_by', 'updated_at'),
        }),
    )
    list_display = ('name', 'email', 'url', 'classification', 'jurisdiction', 'category_list')
    list_filter = (
        'jurisdiction', 'classification', 'categories',
        make_nullfilter('geo', _('Has geo coordinates')),
        make_nullfilter('region', _('Has region')),
        make_emptyfilter('email', 'E-Mail'),
        make_emptyfilter('fax', 'Fax')
    )
    filter_horizontal = ('laws',)
    list_max_show_all = 5000
    search_fields = ['name', 'other_names', 'description']
    exclude = ('confirmed',)
    raw_id_fields = (
        'parent', 'root', '_created_by', '_updated_by',
        'region',
    )
    tag_all_config = ('categories', CATEGORY_AUTOCOMPLETE_URL)
    readonly_fields = ('_created_by', 'created_at', '_updated_by', 'updated_at')

    actions = ClassificationAssignMixin.actions + [
            'export_csv', 'remove_from_index', 'tag_all'
    ]

    def save_model(self, request, obj, form, change):
        obj._updated_by = request.user
        obj.updated_at = timezone.now()
        if change is None:
            obj._created_by = obj._updated_by
            obj.created_at = obj.updated_at

        super(PublicBodyAdminMixin, self).save_model(request, obj, form, change)

    def category_list(self, obj):
        return ", ".join(o.name for o in obj.categories.all())

    def export_csv(self, request, queryset):
        return export_csv_response(PublicBody.export_csv(queryset))
    export_csv.short_description = _("Export to CSV")

    def remove_from_index(self, request, queryset):
        from haystack import connections as haystack_connections

        for obj in queryset:
            for using in haystack_connections.connections_info.keys():
                backend = haystack_connections[using].get_backend()
                backend.remove(obj)

        self.message_user(request, _("Removed from search index"))
    remove_from_index.short_description = _("Remove from search index")


class PublicBodyAdmin(PublicBodyAdminMixin, admin.ModelAdmin):
    pass


class FoiLawAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('name', 'meta', 'law_type', 'jurisdiction',)
    list_filter = ('meta', 'law_type', 'jurisdiction')
    raw_id_fields = ('mediator',)
    filter_horizontal = ('combined',)
    search_fields = ['name', 'description']


class JurisdictionAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_filter = [
        'hidden', 'rank',
        make_nullfilter('region', _('Has region')),
    ]
    list_display = ['name', 'hidden', 'rank']
    raw_id_fields = ('region',)


class PublicBodyTagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_topic", "rank"]
    list_filter = ['is_topic', 'rank']
    ordering = ["rank", "name"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ["name"]}


class TaggedPublicBodyAdmin(admin.ModelAdmin):
    raw_id_fields = ('content_object', 'tag')


AssignParentBase = make_admin_assign_action('parent')


class AssignParentMixin(AssignParentBase):
    def _execute_assign_action(self, obj, fieldname, assign_obj):
        obj.move(assign_obj, 'sorted-child')


class AssignClassificationParentMixin(AssignParentMixin):
    def _get_assign_action_form_class(self, fieldname):
        return get_fk_form_class(PublicBody, 'classification',
                                 self.admin_site)


class ClassificationAdmin(AssignClassificationParentMixin, TreeAdmin):
    fields = ('name', 'slug', '_position', '_ref_node_id',)
    form = movenodeform_factory(Classification)
    prepopulated_fields = {"slug": ["name"]}
    search_fields = ["name"]
    list_display = ('name', 'num_publicbodies', 'publicbody_link')
    actions = AssignClassificationParentMixin.actions

    def get_queryset(self, request):
        """Use this so we can annotate with additional info."""

        qs = super(ClassificationAdmin, self).get_queryset(request)
        return qs.annotate(
            num_publicbodies=Count('publicbody', distinct=True)
        )

    def num_publicbodies(self, obj):
        """# of companies an expert has."""

        return obj.num_publicbodies
    num_publicbodies.short_description = _('# public bodies')

    def publicbody_link(self, obj):
        return format_html('<a href="{}">{}</a>',
            reverse('admin:publicbody_publicbody_changelist') + (
                '?classification__id__exact={}'.format(obj.id)
            ),
            _('Public bodies with this classification')
        )


class AssignCategoryParentMixin(AssignParentMixin):
    def _get_assign_action_form_class(self, fieldname):
        return get_fk_form_class(PublicBody, 'categories',
                                 self.admin_site)


class CategoryAdmin(AssignCategoryParentMixin, TreeAdmin):
    fields = ('name', 'slug', 'is_topic', '_position', '_ref_node_id',)

    form = movenodeform_factory(Category)
    prepopulated_fields = {"slug": ["name"]}
    search_fields = ["name"]
    actions = AssignCategoryParentMixin.actions


class CategorizedPublicBodyAdmin(admin.ModelAdmin):
    raw_id_fields = ('content_object', 'tag')


admin.site.register(PublicBody, PublicBodyAdmin)
admin.site.register(FoiLaw, FoiLawAdmin)
admin.site.register(Jurisdiction, JurisdictionAdmin)
admin.site.register(PublicBodyTag, PublicBodyTagAdmin)
admin.site.register(TaggedPublicBody, TaggedPublicBodyAdmin)
admin.site.register(Classification, ClassificationAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(CategorizedPublicBody, CategorizedPublicBodyAdmin)
