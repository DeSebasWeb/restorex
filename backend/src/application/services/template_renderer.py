"""Template renderer for notification messages.

Uses safe variable substitution — unknown variables are left as-is.
Lives in the application layer (only stdlib, no external dependencies).
"""


class _SafeDict(dict):
    """Dict that returns the key as {key} if missing, instead of raising."""

    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


class TemplateRenderer:
    """Renders notification templates with variable substitution."""

    def render(self, template: str, variables: dict) -> str:
        """Replace {variable} placeholders with values.

        Unknown variables are left as-is (e.g. {unknown} stays as {unknown}).
        """
        return template.format_map(_SafeDict(variables))
