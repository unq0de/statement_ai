import unicodedata

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class SpecialCharacterValidator:
    def validate(self, password, user=None):
        if not any(
            unicodedata.category(character)[0] in {'P', 'S'}
            for character in password
        ):
            raise ValidationError(
                _('This password must contain at least one special character.'),
                code='password_no_special_character',
            )

    def get_help_text(self):
        return _('Your password must contain at least one punctuation mark or symbol.')