"""What every stored text field refuses, whatever the feature (AC-0001-41)."""

import re

# Line breaks and tabs are text a justification may hold; every other C0 control
# character and DEL is not.
CONTROL_CHARACTER = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
CONTROL_CHARACTER_MESSAGE = "O texto tem um caractere inválido. Digite-o de novo, sem colar."
