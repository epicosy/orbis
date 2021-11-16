
class OrbisError(Exception):
    """Generic errors."""
    pass


class CommandError(Exception):
    """Command errors."""
    pass


class NotEmptyDirectory(Exception):
    """Raise when test not found."""
