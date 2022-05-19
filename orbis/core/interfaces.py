from cement import Interface


class HandlersInterface(Interface):
    class Meta:
        interface = "handlers"


class DatabaseInterface(Interface):
    class Meta:
        interface = 'database'

