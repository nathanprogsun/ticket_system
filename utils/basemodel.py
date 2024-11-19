from django.db import models
import uuid
from django.utils import timezone
from django.db.models.signals import post_delete


class BaseModelManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = BaseModelManager()  # Default manager, returns only non-deleted records
    all_objects = (
        models.Manager()
    )  # Manager to query all records, including deleted ones

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False, logical_del=True) -> None:
        if logical_del:
            self.deleted_at = timezone.now()
            self.save()
            # send signal
            post_delete.send(sender=self.__class__, instance=self)
        else:
            super().delete(using, keep_parents)
