import os
import sys

dirs_to_check = [
    os.path.dirname(os.path.abspath(__file__)),
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
]
if "LAMBDA_TASK_ROOT" in os.environ:
    dirs_to_check.insert(0, os.environ["LAMBDA_TASK_ROOT"])

for base in dirs_to_check:
    for sub in ["api", "protocol-runtime", "model-gateway", "worker"]:
        p = os.path.join(base, "services", sub, "src")
        if os.path.exists(p) and p not in sys.path:
            sys.path.insert(0, p)

from lw_care_api.main import create_app
from lw_care_api.config import get_settings

app = create_app(get_settings())
