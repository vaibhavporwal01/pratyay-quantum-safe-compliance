"""Import every module's models here so Alembic sees them."""

import app.audit.models  # noqa: F401
import app.trust.models  # noqa: F401
import app.decision.models
import app.identity.models
import app.loans.models
import app.origination.models
import app.rules.models  # noqa: F401
