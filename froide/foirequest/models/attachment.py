from __future__ import unicode_literals

from django.db import models
from django.conf import settings
from django.dispatch import Signal
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible

from froide.helper.redaction import can_redact_file
from froide.helper.storage import HashedFilenameStorage
from froide.helper.document import PDF_FILETYPES
from froide.document.models import Document

from .message import FoiMessage


def upload_to(instance, filename):
    # name will be irrelevant
    # as hashed filename storage will drop it
    # and use only directory
    return "%s/%s" % (settings.FOI_MEDIA_PATH, instance.name)


@python_2_unicode_compatible
class FoiAttachment(models.Model):
    belongs_to = models.ForeignKey(FoiMessage, null=True,
            verbose_name=_("Belongs to request"), on_delete=models.CASCADE)
    name = models.CharField(_("Name"), max_length=255)
    file = models.FileField(
        _("File"), upload_to=upload_to, max_length=255,
        storage=HashedFilenameStorage()
    )
    size = models.IntegerField(_("Size"), blank=True, null=True)
    filetype = models.CharField(_("File type"), blank=True, max_length=100)
    format = models.CharField(_("Format"), blank=True, max_length=100)
    can_approve = models.BooleanField(_("User can approve"), default=True)
    approved = models.BooleanField(_("Approved"), default=False)
    redacted = models.ForeignKey('self', verbose_name=_("Redacted Version"),
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name='unredacted_set')
    is_redacted = models.BooleanField(_("Is redacted"), default=False)
    converted = models.ForeignKey('self', verbose_name=_("Converted Version"),
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name='original_set')
    is_converted = models.BooleanField(_("Is converted"), default=False)

    document = models.ForeignKey(
        Document, null=True, blank=True,
        on_delete=models.SET_NULL
    )

    attachment_published = Signal(providing_args=[])

    class Meta:
        ordering = ('name',)
        unique_together = (("belongs_to", "name"),)
        # order_with_respect_to = 'belongs_to'
        verbose_name = _('Attachment')
        verbose_name_plural = _('Attachments')

    def __str__(self):
        return "%s (%s) of %s" % (self.name, self.size, self.belongs_to)

    def index_content(self):
        return "\n".join((self.name,))

    def get_html_id(self):
        return _("attachment-%(id)d") % {"id": self.id}

    def get_internal_url(self):
        return settings.MEDIA_URL + self.file.name

    @property
    def can_redact(self):
        return can_redact_file(self.filetype, name=self.name)

    @property
    def is_pdf(self):
        return self.filetype in PDF_FILETYPES

    def get_anchor_url(self):
        if self.belongs_to:
            return '%s#%s' % (self.belongs_to.request.get_absolute_url(),
                self.get_html_id())
        return '#' + self.get_html_id()

    def get_domain_anchor_url(self):
        return '%s%s' % (settings.SITE_URL, self.get_anchor_url())

    def get_absolute_url(self):
        fr = self.belongs_to.request
        return reverse(
            'foirequest-show_attachment',
            kwargs={
                'slug': fr.slug,
                'message_id': self.belongs_to.pk,
                'attachment_name': self.name
            }
        )

    def get_absolute_domain_url(self):
        return '%s%s' % (settings.SITE_URL, self.get_absolute_url())

    def get_absolute_file_url(self):
        if settings.USE_X_ACCEL_REDIRECT:
            if not self.name:
                return ''
            return reverse('foirequest-auth_message_attachment',
                kwargs={
                    'message_id': self.belongs_to_id,
                    'attachment_name': self.name
                })
        else:
            if self.file:
                return self.file.url

    def get_absolute_domain_file_url(self):
        return '%s%s' % (settings.SITE_URL, self.get_absolute_file_url())

    def approve_and_save(self):
        self.approved = True
        self.save()
        self.attachment_published.send(sender=self)

    def create_document(self):
        if self.document is not None:
            return self.document

        if self.is_pdf:
            return

        foirequest = self.belongs_to.request
        doc = Document.objects.create(
            original=self.file.name,
            user=foirequest.user,
            public=foirequest.public,
            title=self.name
        )
        self.document = doc
        self.save()
        return doc
