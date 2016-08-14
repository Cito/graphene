from collections import OrderedDict
import six

from ..utils.is_base_type import is_base_type
from .options import Options

from .abstracttype import AbstractTypeMeta
from .utils import get_fields_in_type, yank_fields_from_attrs, merge_fields_in_attrs
from .interface import Interface


class ObjectTypeMeta(AbstractTypeMeta):

    def __new__(cls, name, bases, attrs):
        # Also ensure initialization is only performed for subclasses of
        # ObjectType
        if not is_base_type(bases, ObjectTypeMeta):
            return type.__new__(cls, name, bases, attrs)

        options = Options(
            attrs.pop('Meta', None),
            name=name,
            description=attrs.get('__doc__'),
            interfaces=(),
        )

        attrs = merge_fields_in_attrs(bases, attrs)
        options.local_fields = get_fields_in_type(ObjectType, attrs)
        yank_fields_from_attrs(attrs, options.local_fields)
        options.interface_fields = OrderedDict()
        for interface in options.interfaces:
            assert issubclass(interface, Interface), (
                'All interfaces of {} must be a subclass of Interface. Received "{}".'
            ).format(name, interface)
            options.interface_fields.update(interface._meta.fields)
        options.fields = OrderedDict(options.interface_fields)
        options.fields.update(options.local_fields)

        cls = type.__new__(cls, name, bases, dict(attrs, _meta=options))
        for interface in options.interfaces:
            interface.implements(cls)

        return cls

    def __str__(cls):
        return cls._meta.name


class ObjectType(six.with_metaclass(ObjectTypeMeta)):

    is_type_of = None

    def __init__(self, *args, **kwargs):
        # GraphQL ObjectType acting as container
        args_len = len(args)
        fields = self._meta.fields.items()
        if args_len > len(fields):
            # Daft, but matches old exception sans the err msg.
            raise IndexError("Number of args exceeds number of fields")
        fields_iter = iter(fields)

        if not kwargs:
            for val, (name, field) in zip(args, fields_iter):
                setattr(self, name, val)
        else:
            for val, (name, field) in zip(args, fields_iter):
                setattr(self, name, val)
                kwargs.pop(name, None)

        for name, field in fields_iter:
            try:
                val = kwargs.pop(name)
                setattr(self, name, val)
            except KeyError:
                pass

        if kwargs:
            for prop in list(kwargs):
                try:
                    if isinstance(getattr(self.__class__, prop), property):
                        setattr(self, prop, kwargs.pop(prop))
                except AttributeError:
                    pass
            if kwargs:
                raise TypeError(
                    "'{}' is an invalid keyword argument for {}".format(
                        list(kwargs)[0],
                        self.__class__.__name__
                    )
                )
