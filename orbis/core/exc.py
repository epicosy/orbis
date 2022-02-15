
class OrbisError(Exception):
    """Generic errors."""
    pass


class CommandError(Exception):
    """Command errors."""
    pass


class NotEmptyDirectory(Exception):
    """Raise when test not found."""


class OrbisError400(Exception):
    """Exception for 400 HTTP code."""
