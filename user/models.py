from django.db import models
from django.contrib.auth.base_user import AbstractBaseUser
from utils.basemodel import BaseModel


class User(AbstractBaseUser, BaseModel):
    first_name = models.CharField(max_length=150, null=False, blank=False)
    last_name = models.CharField(max_length=150, null=False, blank=False)
    email = models.EmailField(unique=True, db_index=True, null=False, blank=False)

    class Meta:
        db_table = "user"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["first_name", "last_name"]),
        ]

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.name
