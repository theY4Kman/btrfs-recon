class classproperty(property):
    """A decorator that behaves like @property except that operates
    on classes rather than instances.

    NOTE: this implementation is lifted directly from sqlalchemy.util.langhelpers.classproperty,
          but doesn't cause the ORM to try to lift mappable properties from it.
          see sqlalchemy/orm/decl_base.py:674 (_extract_mappable_attributes)

    """

    def __init__(self, fget, *arg, **kw):
        super(classproperty, self).__init__(fget, *arg, **kw)
        self.__doc__ = fget.__doc__

    def __get__(desc, self, cls):
        return desc.fget(cls)
